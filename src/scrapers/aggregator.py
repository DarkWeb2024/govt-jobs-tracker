"""Aggregator source (FreeJobAlert). Aggregators cast a wide net but are
never trusted on their own: records from here stay Unverified until an
official domain link is attached (verify.py handles the promotion)."""
import re

from ..models import Notification
from .base import soup, clean

PAGES = [
    "https://www.freejobalert.com/latest-notifications/",
    "https://www.freejobalert.com/government-jobs/",
]


def scrape():
    out = []
    for page_url in PAGES:
        page = soup(page_url)
        if page is None:
            continue
        for a in page.select("a[href]"):
            t = clean(a.get_text())
            low = t.lower()
            if len(t) < 25:
                continue
            if not re.search(r"(recruitment|apply online|notification|vacanc|posts)", low):
                continue
            if re.search(r"(result|answer key|admit card|syllabus|cut ?off)", low):
                continue
            out.append(Notification(
                job_name=t[:180],
                organization="",
                category="Job",
                state="",
                official_website="",
                apply_link=a["href"],
                verification_source="aggregator:freejobalert.com",
                tags="aggregator",
                notes="Found via aggregator - needs official confirmation",
            ))
    # de-dup within the page set
    seen, unique = set(), []
    for n in out:
        if n.notification_id not in seen:
            seen.add(n.notification_id)
            unique.append(n)
    return unique
