"""High Court of Karnataka recruitment notifications."""
from ..models import Notification
from .base import soup, clean

URL = "https://judiciary.karnataka.gov.in/"


def scrape():
    page = soup(URL)
    if page is None:
        return []
    out = []
    for a in page.select("a[href]"):
        t = clean(a.get_text())
        low = t.lower()
        if len(t) < 12:
            continue
        if not any(k in low for k in ("recruitment", "notification no", "hcrb",
                                      "direct recruitment", "posts of")):
            continue
        href = a["href"]
        url = href if href.startswith("http") else URL.rstrip("/") + "/" + href.lstrip("/")
        out.append(Notification(
            job_name=t[:180],
            organization="High Court of Karnataka",
            department="Karnataka Judiciary",
            category="Job",
            state="Karnataka",
            location="Bengaluru",
            official_website=URL,
            apply_link=url,
            official_pdf=url if url.lower().endswith(".pdf") else "",
            verification_source="official:judiciary.karnataka.gov.in",
            tags="karnataka,high court,state",
        ))
    return out
