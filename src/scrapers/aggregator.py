"""Aggregator source (FreeJobAlert). Aggregators cast a wide net but are
never trusted on their own: records from here stay Unverified until an
official domain link is attached (verify.py handles the promotion).

Each page carries a state hint so the Karnataka-specific listing is tagged
Karnataka (and survives the location filter / lands in the Karnataka scope),
while the all-India pages stay unscoped."""
import re

from ..models import Notification
from .base import soup, clean

# (url, state_hint). Karnataka page first so its state tag wins the de-dup for
# any posting that also appears on an all-India page.
PAGES = [
    ("https://www.freejobalert.com/karnataka-government-jobs/", "Karnataka"),
    ("https://www.freejobalert.com/", ""),
    ("https://www.freejobalert.com/latest-notifications/", ""),
    ("https://www.freejobalert.com/government-jobs/", ""),
]


def _category(title):
    low = title.lower()
    if "apprentice" in low:
        return "Apprenticeship"
    if any(k in low for k in ("exam", "cgl", "chsl", " net ", "gate", "tet", "cet")):
        return "Exam"
    return "Job"


def _vacancies(title):
    m = re.search(r"(\d{1,6})\+?\s*(?:posts?|vacanc|seat)", title, re.I)
    if m:
        return m.group(1)
    # titles like "ISRO 244 Assistant ... Online Form" put the count up front;
    # take the first 2-6 digit number that is not a year
    for num in re.findall(r"\b(\d{2,6})\b", title):
        if not re.fullmatch(r"(19|20)\d\d", num):
            return num
    return ""


def scrape():
    out = []
    for page_url, state in PAGES:
        page = soup(page_url)
        if page is None:
            continue
        for a in page.select("a[href]"):
            t = clean(a.get_text())
            low = t.lower()
            if len(t) < 25:
                continue
            if not re.search(r"(recruitment|apply online|notification|vacanc|posts|online form|vacancy)", low):
                continue
            if "syllabus" in low:
                continue
            # admit card / result / answer key posts pass through - the pipeline
            # routes them to the applied-updates watcher instead of new records
            out.append(Notification(
                job_name=t[:180],
                organization=t.split(" Vacancy")[0].split(" Recruitment")[0]
                             .split(" Various")[0][:60],
                category=_category(t),
                state=state, location=state,
                vacancies=_vacancies(t),
                official_website="",
                apply_link=a["href"],
                verification_source="aggregator:freejobalert.com",
                tags="aggregator,freejobalert" + (",karnataka" if state else ""),
                notes="Found via aggregator - needs official confirmation",
            ))
    # de-dup within the page set (keep the first occurrence; Karnataka page is
    # scanned first so a posting listed there keeps its Karnataka tag)
    seen, unique = set(), []
    for n in out:
        if n.notification_id not in seen:
            seen.add(n.notification_id)
            unique.append(n)
    return unique
