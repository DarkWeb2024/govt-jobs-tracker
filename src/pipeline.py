"""Daily pipeline: scrape -> filter -> verify -> store -> outputs -> notify."""
import json
import os
import shutil
from datetime import datetime, timedelta

import yaml

from . import filters, priority, verify
from .database import Store
from .logger import get_logger
from .models import Notification
from .outputs import excel_out, pdf_out, website
from .outputs.tabular import write_csv, write_json, write_markdown
from .notify import emailer, mstodo, whatsapp
from .scrapers.registry import enabled_scrapers

log = get_logger("pipeline")


def load_config(path="config/config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def seed_if_empty(store, seed_path="data/seed.json"):
    if store.all() or not os.path.exists(seed_path):
        return 0
    with open(seed_path, encoding="utf-8") as f:
        records = json.load(f)
    for rec in records:
        n = Notification(**rec)
        verify.apply(n)
        priority.assign(n)
        store.upsert(n)
        if rec.get("status") and rec["status"] != "Not Applied":
            store.set_status(n.notification_id, rec["status"])
    log.info("seeded %d curated notifications", len(records))
    return len(records)


def collect(cfg):
    found, errors = [], 0
    for name, fn in enabled_scrapers(cfg).items():
        try:
            items = fn()
            log.info("source %-22s -> %d raw items", name, len(items))
            found.extend(items)
        except Exception as e:
            errors += 1
            log.error("source %s crashed: %s", name, e)
    return found, errors


def run(cfg_path="config/config.yaml"):
    started = datetime.now().isoformat(timespec="seconds")
    cfg = load_config(cfg_path)
    store = Store(cfg["paths"]["database"])
    seed_if_empty(store)

    raw, errors = collect(cfg)
    new = updated = 0
    for n in raw:
        if not filters.passes(n, cfg):
            continue
        verify.apply(n)
        priority.assign(n)
        result = store.upsert(n)
        new += result == "new"
        updated += result == "updated"

    # refresh derived fields on everything (deadlines move every day)
    everything = []
    for n in store.all():
        priority.assign(n)
        d = n.to_dict()
        store.conn.execute(
            "UPDATE notifications SET data=? WHERE notification_id=?",
            (json.dumps(d, ensure_ascii=False), n.notification_id))
        everything.append(n)
    store.conn.commit()

    everything.sort(key=lambda n: (n.days_left() if n.days_left() is not None
                                   and n.days_left() >= 0 else 9999))

    # outputs
    stamp = datetime.now().strftime("%Y-%m-%d")
    rep = cfg["paths"]["reports"]
    daily = os.path.join(rep, "Daily")
    csv_p = write_csv(everything, os.path.join(rep, "CSV", f"tracker_{stamp}.csv"))
    xlsx_p = excel_out.write_excel(everything, os.path.join(rep, "Excel", f"tracker_{stamp}.xlsx"))
    yesterday = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
    changes = store.changes_since(yesterday)
    pdf_p = pdf_out.write_pdf(everything, os.path.join(rep, "PDF", f"report_{stamp}.pdf"),
                              changes=changes)
    write_json(everything, os.path.join(daily, f"data_{stamp}.json"))
    write_markdown(everything, os.path.join(daily, f"summary_{stamp}.md"))
    # weekly / monthly snapshots + archive
    if datetime.now().weekday() == 6:
        shutil.copy(pdf_p, os.path.join(_mk(rep, "Weekly"), f"week_ending_{stamp}.pdf"))
    if datetime.now().day == 1:
        shutil.copy(pdf_p, os.path.join(_mk(rep, "Monthly"), f"month_{stamp}.pdf"))
    shutil.copy(csv_p, os.path.join(_mk(rep, "Archive"), f"tracker_{stamp}.csv"))

    # website (docs/ for GitHub Pages) with latest export copies
    site_dir = website.build_site(everything, cfg["paths"]["site"])
    for src, name in [(csv_p, "latest.csv"), (xlsx_p, "latest.xlsx"), (pdf_p, "latest.pdf")]:
        shutil.copy(src, os.path.join(site_dir, "data", name))

    # notifications
    emailer.send_daily(cfg, everything, changes, [pdf_p, csv_p, xlsx_p])
    mstodo.sync(cfg, everything)
    whatsapp.send(cfg, everything)

    summary = (f"new={new} updated={updated} total={len(everything)} "
               f"errors={errors} changes24h={len(changes)}")
    store.record_run(started, new, updated, errors, summary)
    log.info("run complete: %s", summary)
    return summary


def _mk(rep, sub):
    p = os.path.join(rep, sub)
    os.makedirs(p, exist_ok=True)
    return p
