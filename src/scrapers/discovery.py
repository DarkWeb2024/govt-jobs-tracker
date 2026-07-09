"""Extra discovery sources: indgovtjobs.in, sarkariresult.com, karnatakacareers.org.

Like every aggregator, these only widen the discovery net. Records from here
carry verification_source="aggregator:<domain>" and stay Unverified unless an
official-domain link is attached (verify.py handles promotion). Parsing is
kept generic on purpose - these sites reshuffle their layouts often, so we
look for anchors whose text reads like a recruitment title rather than
depending on any specific CSS structure."""
import re
from urllib.parse import urlparse

from ..models import Notification
from .base import soup, clean

TITLE_HINTS = ("recruitment", "vacancy", "posts", "notification", "online form",
               "apprentice", "admit card", "result", "answer key", "bharti")
SKIP_HINTS = ("privacy", "contact", "about us", "disclaimer", "syllabus pdf",
              "current affairs", "quiz", "mock test", "study material", "coaching")


def _looks_like_notification(text):
    low = text.lower()
    if len(text) < 22 or len(text) > 200:
        return False
    if any(k in low for k in SKIP_HINTS):
        return False
    if not any(k in low for k in TITLE_HINTS):
        return False
    # a plausible recruitment headline names a year or a post count
    return bool(re.search(r"20\d\d|\d{2,6}\s*(post|vacanc|seat)", low))


def _category(text):
    low = text.lower()
    if "apprentice" in low:
        return "Apprenticeship"
    if any(k in low for k in ("exam", "cgl", "chsl", "net ", "gate", "tet")):
        return "Exam"
    return "Job"


def _harvest(url, org_label, state="", limit=40):
    page = soup(url)
    if page is None:
        return []
    domain = urlparse(url).netloc.removeprefix("www.")
    out, seen = [], set()
    for a in page.select("a[href]"):
        t = clean(a.get_text())
        if not _looks_like_notification(t):
            continue
        href = a["href"]
        if not href.startswith("http"):
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(Notification(
            job_name=t[:180],
            organization=org_label or t.split()[0],
            category=_category(t),
            state=state or "All India", location=state or "All India",
            apply_link=href,
            verification_source=f"aggregator:{domain}",
            notes="Found via aggregator - needs official confirmation",
            tags=f"aggregator,{domain}"))
        if len(out) >= limit:
            break
    return out


def indgovtjobs():
    return (_harvest("https://www.indgovtjobs.in/", "") +
            _harvest("https://ka.indgovtjobs.net/", "", state="Karnataka"))


def sarkariresult():
    return _harvest("https://www.sarkariresult.com/latestjob/", "")


def karnatakacareers():
    return (_harvest("https://www.karnatakacareers.org/", "", state="Karnataka") +
            _harvest("https://www.karnatakacareers.org/district/bengaluru/", "",
                     state="Karnataka"))
