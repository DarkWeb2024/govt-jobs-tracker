"""Karnataka Examinations Authority - active recruitment application links."""
from ..models import Notification
from .base import soup, clean

URL = "https://cetonline.karnataka.gov.in/kea/"


def scrape():
    page = soup(URL)
    if page is None:
        return []
    out = []
    for a in page.select("a[href]"):
        t = clean(a.get_text())
        low = t.lower()
        if len(t) < 10:
            continue
        if not any(k in low for k in ("recruitment", "2026", "constable", "notification")):
            continue
        if any(k in low for k in ("result", "answer key", "admit", "hall ticket", "cet ")):
            continue
        href = a["href"]
        url = href if href.startswith("http") else URL + href.lstrip("/")
        out.append(Notification(
            job_name=f"KEA: {t}"[:180],
            organization="Karnataka Examinations Authority",
            department="Government of Karnataka",
            category="Job",
            state="Karnataka",
            location="Karnataka",
            official_website=URL,
            apply_link=url,
            verification_source="official:cetonline.karnataka.gov.in",
            tags="karnataka,kea,state",
        ))
    return out
