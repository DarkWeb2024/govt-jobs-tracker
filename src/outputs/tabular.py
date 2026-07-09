"""CSV, JSON, Markdown and RSS outputs."""
import csv
import json
import os
from datetime import datetime

FIELDS = [
    "notification_id", "job_name", "exam_name", "department", "organization",
    "qualification", "age", "salary", "pay_level", "vacancies", "state", "location",
    "category", "application_start", "application_end", "exam_date", "result_date",
    "official_website", "official_pdf", "apply_link", "selection_process",
    "application_fee", "status", "verification_status", "verification_source",
    "verification_timestamp", "confidence", "priority", "notes", "tags",
    "first_seen", "last_checked",
]


def write_csv(notifications, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS + ["days_left"], extrasaction="ignore")
        w.writeheader()
        for n in notifications:
            d = n.to_dict()
            d["days_left"] = n.days_left()
            w.writerow(d)
    return path


def write_json(notifications, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "count": len(notifications),
        "notifications": [dict(n.to_dict(), days_left=n.days_left())
                          for n in notifications],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    return path


def write_markdown(notifications, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [f"# Government Jobs & Exams - {datetime.now():%d %b %Y}", ""]
    for section, items in [
        ("Closing within 7 days", [n for n in notifications
                                   if (n.days_left() is not None and 0 <= n.days_left() <= 7)]),
        ("Open now", [n for n in notifications
                      if n.verification_status not in ("Application Closed", "Expired")
                      and (n.days_left() is None or n.days_left() >= 0)]),
    ]:
        lines.append(f"## {section}")
        if not items:
            lines.append("Nothing in this bucket today.")
        for n in items:
            dl = n.days_left()
            lines.append(f"- **{n.job_name}** ({n.organization}) - last date "
                         f"{n.application_end or 'TBA'}"
                         + (f" ({dl} days left)" if dl is not None else "")
                         + f" - {n.verification_status} - [link]({n.apply_link or n.official_website})")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def write_rss(notifications, path, site_url):
    from feedgen.feed import FeedGenerator
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fg = FeedGenerator()
    fg.id(site_url)
    fg.title("Government Jobs & Exams Intelligence Tracker")
    fg.link(href=site_url)
    fg.description("Daily verified government job and exam notifications (Central + Karnataka)")
    fg.language("en")
    for n in notifications[:100]:
        fe = fg.add_entry()
        fe.id(n.notification_id)
        fe.title(f"[{n.verification_status}] {n.job_name}")
        fe.link(href=n.apply_link or n.official_website or site_url)
        fe.description(f"{n.organization} | Last date: {n.application_end or 'TBA'} | "
                       f"Priority: {n.priority} | {n.qualification}")
    fg.rss_file(path)
    return path
