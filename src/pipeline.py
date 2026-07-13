"""Daily pipeline: scrape -> filter -> verify -> store -> outputs -> notify."""
import json
import os
import re
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


# announcements about an existing recruitment rather than a new one
UPDATE_PAT = re.compile(
    r"admit card|hall ticket|result|answer key|merit list|score ?card|"
    r"correction window|corrigendum|exam (?:date|city|schedule)|interview (?:schedule|list)|"
    r"document verification|cut ?off", re.I)


def track_applied_updates(store, update_items):
    """Match admit-card/result/answer-key announcements from any source
    against the records the user has applied to. A hit is appended to the
    record's notes (history-logged), so it lands in the daily changes email."""
    from .models import is_applied
    applied = [n for n in store.all() if is_applied(n.status)]
    if not applied or not update_items:
        return 0
    matched = 0
    today = datetime.now().strftime("%Y-%m-%d")
    for item in update_items:
        low = (item.job_name + " " + item.organization).lower()
        low_tokens = set(re.split(r"\W+", low))
        for a in applied:
            org_words = [w for w in re.split(r"\W+", a.organization) if w]
            org_tokens = {w.lower() for w in org_words if len(w) > 2}
            if len(org_words) > 1:      # "State Bank of India" also matches "SBI"
                org_tokens.add("".join(w[0] for w in org_words if w[0].isupper()).lower())
            name_tokens = {t for t in re.split(r"\W+", a.job_name.lower())
                           if len(t) > 3 and not t.isdigit()}
            if not org_tokens & low_tokens:
                continue
            overlap = sum(1 for t in name_tokens if t in low)
            if overlap < 2:
                continue
            note = f"Update {today}: {item.job_name[:120]} -> {item.apply_link or item.official_website}"
            if item.job_name[:60].lower() in (a.notes or "").lower():
                continue    # already recorded on a previous run
            store.append_note(a.notification_id, note)
            log.info("applied-update matched: %s <- %s", a.job_name[:50], item.job_name[:60])
            matched += 1
    return matched


def update_org_registry(notifications, path="data/organizations.json"):
    """Append organizations seen in notifications but missing from the master
    registry, so the registry grows on its own. Only records that carry an
    official website are added (aggregator noise stays out)."""
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    orgs = data.get("organizations", [])
    known = {o["name"].lower() for o in orgs} | {o.get("short", "").lower() for o in orgs}
    added = 0
    for n in notifications:
        name = (n.organization or "").strip()
        if not name or len(name) < 3 or name.lower() in known:
            continue
        if not n.official_website or not verify.is_official(n.official_website):
            continue
        orgs.append({"name": name, "short": name[:20].upper().replace(" ", "-"),
                     "type": "auto-discovered", "state": n.state or "All India",
                     "website": n.official_website,
                     "careers": n.apply_link or n.official_website})
        known.add(name.lower())
        added += 1
    if added:
        data["organizations"] = orgs
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log.info("organization registry: %d new organizations added (total %d)",
                 added, len(orgs))
    return added


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
    # announcements about existing recruitments (results, admit cards, keys)
    # feed the applied-updates watcher instead of becoming new records
    update_items = [n for n in raw if UPDATE_PAT.search(n.job_name)]
    raw = [n for n in raw if not UPDATE_PAT.search(n.job_name)]
    matched_updates = track_applied_updates(store, update_items)

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
    yesterday = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
    changes = store.changes_since(yesterday)
    history = store.changes_since("1970-01-01")[:500]
    xlsx_p = excel_out.write_excel(everything, os.path.join(rep, "Excel", f"tracker_{stamp}.xlsx"),
                                   history=history)
    pdf_p = pdf_out.write_pdf(everything, os.path.join(rep, "PDF", f"report_{stamp}.pdf"),
                              changes=changes)
    write_json(everything, os.path.join(daily, f"data_{stamp}.json"))
    write_markdown(everything, os.path.join(daily, f"summary_{stamp}.md"))
    # weekly / monthly snapshots + archive
    if datetime.now().weekday() == 6:
        shutil.copy(pdf_p, os.path.join(_mk(rep, "Weekly"), f"week_ending_{stamp}.pdf"))
    if datetime.now().day == 1:
        shutil.copy(pdf_p, os.path.join(_mk(rep, "Monthly"), f"month_{stamp}.pdf"))
    if datetime.now().month == 1 and datetime.now().day == 1:
        shutil.copy(pdf_p, os.path.join(_mk(rep, "Yearly"), f"year_{stamp}.pdf"))
        shutil.copy(csv_p, os.path.join(_mk(rep, "Yearly"), f"year_{stamp}.csv"))
    shutil.copy(csv_p, os.path.join(_mk(rep, "Archive"), f"tracker_{stamp}.csv"))

    update_org_registry(everything)

    # website (docs/ for GitHub Pages) with latest export copies
    site_dir = website.build_site(everything, cfg["paths"]["site"])
    for src, name in [(csv_p, "latest.csv"), (xlsx_p, "latest.xlsx"), (pdf_p, "latest.pdf")]:
        shutil.copy(src, os.path.join(site_dir, "data", name))

    # notifications - records the user hid stay out of every alert channel
    from .models import HIDDEN_STATES
    visible = [n for n in everything if n.status not in HIDDEN_STATES]
    emailer.send_daily(cfg, visible, changes, [pdf_p, csv_p, xlsx_p])
    mstodo.sync(cfg, visible)
    whatsapp.send(cfg, visible)

    summary = (f"new={new} updated={updated} total={len(everything)} "
               f"errors={errors} changes24h={len(changes)} "
               f"applied_updates={matched_updates}")
    store.record_run(started, new, updated, errors, summary)
    log.info("run complete: %s", summary)
    return summary


def _mk(rep, sub):
    p = os.path.join(rep, sub)
    os.makedirs(p, exist_ok=True)
    return p
