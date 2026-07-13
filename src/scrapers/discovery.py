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


# indgovtjobs.in runs on Blogspot, which exposes a JSON feed of every recent
# post with its labels - far more complete than the homepage (135 posts vs 6).
INDGOVT_FEEDS = [
    ("https://www.indgovtjobs.in/feeds/posts/default?alt=json&max-results=150", ""),
]
HUB_LABELS = {"education wise govt jobs", "qualification wise", "state wise"}
INDIAN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh", "goa",
    "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka", "kerala",
    "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram", "nagaland",
    "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu", "telangana", "tripura",
    "uttar pradesh", "uttarakhand", "west bengal", "delhi", "jammu kashmir",
    "ladakh", "puducherry", "chandigarh", "andaman and nicobar", "lakshadweep",
    "daman and diu", "dadra and nagar haveli",
}
CITY_STATE = {
    "bangalore": "Karnataka", "bengaluru": "Karnataka", "mysore": "Karnataka",
    "mysuru": "Karnataka", "hubli": "Karnataka", "mangalore": "Karnataka",
    "chennai": "Tamil Nadu", "mumbai": "Maharashtra", "pune": "Maharashtra",
    "hyderabad": "Telangana", "kolkata": "West Bengal", "lucknow": "Uttar Pradesh",
    "ahmedabad": "Gujarat", "jaipur": "Rajasthan", "kochi": "Kerala",
}


def _feed_state(cats, title, default):
    """Map a post to a state using its labels ('Karnataka Jobs') or a city
    named in the title, so the location filter can judge it correctly."""
    for c in cats:
        base = re.sub(r"\s+(?:govt\s+)?jobs?$", "", c, flags=re.I).strip().lower()
        if base in INDIAN_STATES:
            return base.title()
    low = title.lower()
    for city, state in CITY_STATE.items():
        if city in low:
            return state
    return default


def _title_meta(title):
    """Pull last-date and vacancy count out of headline text like
    '... Apply Online for 6715 Posts | Last Date 21-07-2026'."""
    end = ""
    m = re.search(r"last\s+date[:\s]*(\d{1,2})[-./](\d{1,2})[-./](\d{4})", title, re.I)
    if m:
        end = f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    vac = ""
    m = re.search(r"(\d{2,6})\+?\s*(?:posts|vacanc)", title, re.I)
    if m:
        vac = m.group(1)
    return end, vac


def indgovtjobs():
    from .base import fetch
    out = []
    for feed_url, default_state in INDGOVT_FEEDS:
        r = fetch(feed_url)
        if r is None:
            continue
        try:
            entries = r.json().get("feed", {}).get("entry", [])
        except ValueError:
            continue
        domain = urlparse(feed_url).netloc.removeprefix("www.")
        for e in entries:
            title = clean(e.get("title", {}).get("$t", ""))
            cats = [c.get("term", "") for c in e.get("category", [])]
            low = title.lower()
            if not title or any(c.lower() in HUB_LABELS for c in cats):
                continue   # listicle hub pages ("Govt Jobs for Diploma Holders")
            if not any(k in low for k in TITLE_HINTS):
                continue
            if any(k in low for k in ("admit card", "result", "answer key", "syllabus")):
                continue   # tracked separately once the record exists
            link = next((l["href"] for l in e.get("link", [])
                         if l.get("rel") == "alternate"), "")
            end, vac = _title_meta(title)
            state = _feed_state(cats, title, default_state)
            out.append(Notification(
                job_name=title[:180],
                organization=title.split(" Recruitment")[0].split(" Vacancy")[0][:60],
                category=_category(title),
                state=state or "All India", location=state or "All India",
                application_end=end, vacancies=vac,
                apply_link=link,
                verification_source=f"aggregator:{domain}",
                notes="Found via aggregator - needs official confirmation",
                tags=f"aggregator,{domain}," + ",".join(cats[:4]).lower()))
    # the Karnataka sub-site is not Blogspot; harvest its HTML directly
    out.extend(_harvest("https://ka.indgovtjobs.net/", "", state="Karnataka"))
    return out


def sarkariresult():
    return _harvest("https://www.sarkariresult.com/latestjob/", "")


def karnatakacareers():
    return (_harvest("https://www.karnatakacareers.org/", "", state="Karnataka") +
            _harvest("https://www.karnatakacareers.org/district/bengaluru/", "",
                     state="Karnataka"))
