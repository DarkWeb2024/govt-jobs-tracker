"""ISRO careers listing (isro.gov.in) - static HTML table, reliable.

Table columns: centre | post title | advertisement no | opens | closes.
Rows carry no anchors (detail pages are JS-driven), so the listing page
itself is used as the apply link; it is the official source either way."""
import re

from ..models import Notification
from .base import soup, clean

LIST_URL = "https://www.isro.gov.in/ViewAllOpportunities.html"

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}

BLR_CENTRES = ("istrac", "ursc", "u r rao", "leos", "isro headquarters", "antrix")


def _parse_date(text):
    m = re.search(r"([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})", text or "")
    if m and m.group(1).lower() in MONTHS:
        return f"{int(m.group(3)):04d}-{MONTHS[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", text or "")
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    return ""


def scrape():
    page = soup(LIST_URL)
    if page is None:
        return []
    out = []
    for tr in page.select("tr"):
        cells = [clean(td.get_text(" ")) for td in tr.find_all("td")]
        if len(cells) < 4:
            continue
        centre, title = cells[0], cells[1]
        advt = cells[2] if len(cells) > 2 else ""
        closes = _parse_date(cells[-1]) or _parse_date(cells[-2] if len(cells) > 4 else "")
        opens = _parse_date(cells[3]) if len(cells) > 4 else ""
        if not title or len(title) < 12:
            continue
        low = (centre + " " + title).lower()
        if not any(k in low for k in ("recruit", "apprentice", "fellow", "scientist",
                                      "technician", "assistant", "engineer")):
            continue
        blr = any(c in low for c in BLR_CENTRES)
        out.append(Notification(
            job_name=f"ISRO {advt}: {title}"[:180] if advt else f"ISRO: {title}"[:180],
            organization="ISRO",
            department=centre[:120] or "Department of Space",
            category="Apprenticeship" if "apprentice" in low else "Job",
            state="All India",
            location="Bengaluru" if blr else (centre[:80] or "ISRO centres"),
            application_start=opens,
            application_end=closes,
            official_website=LIST_URL,
            apply_link=LIST_URL,
            verification_source="official:isro.gov.in",
            tags="isro,space,central" + (",bengaluru" if blr else ""),
            notes=f"Advertisement {advt}" if advt else "",
        ))
    return out
