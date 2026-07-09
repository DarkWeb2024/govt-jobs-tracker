"""Central portals: UPSC, SSC, RRB, IBPS, Agnipath Vayu, Employment News.

SSC and IBPS render most content client-side or ship broken cert chains,
so these scrapers try known endpoints and degrade gracefully. Whatever
cannot be read directly still reaches the tracker through the aggregator
source (tagged Unverified until an official link confirms it)."""
import re

from ..models import Notification
from .base import soup, fetch, clean


def upsc():
    page = soup("https://upsc.gov.in/")
    if page is None:
        return []
    out = []
    for a in page.select("a[href]"):
        t = clean(a.get_text())
        low = t.lower()
        if len(t) < 15:
            continue
        if not any(k in low for k in ("recruitment", "examination", "advt", "vacancy",
                                      "online recruitment application")):
            continue
        href = a["href"]
        url = href if href.startswith("http") else "https://upsc.gov.in" + href
        out.append(Notification(
            job_name=f"UPSC: {t}"[:180], organization="UPSC",
            department="Union Public Service Commission", category="Exam",
            state="All India", location="All India",
            official_website="https://upsc.gov.in/",
            apply_link=url,
            official_pdf=url if url.lower().endswith(".pdf") else "",
            verification_source="official:upsc.gov.in",
            tags="upsc,central,exam"))
    return out


def ssc():
    # ssc.gov.in is an SPA; its public notice board is served from an API.
    # Try the API first, fall back silently (aggregator covers the gap).
    r = fetch("https://ssc.gov.in/api/public/notice-boards?page=0&size=25")
    out = []
    if r is not None and r.headers.get("content-type", "").startswith("application/json"):
        try:
            data = r.json()
            items = data.get("content") or data.get("data") or []
            for it in items:
                title = clean(str(it.get("noticeBoardName") or it.get("title") or ""))
                if not title:
                    continue
                pdf = it.get("filePath") or it.get("url") or ""
                if pdf and not str(pdf).startswith("http"):
                    pdf = "https://ssc.gov.in" + str(pdf)
                out.append(Notification(
                    job_name=f"SSC: {title}"[:180], organization="SSC",
                    department="Staff Selection Commission", category="Exam",
                    state="All India", location="All India",
                    official_website="https://ssc.gov.in/",
                    official_pdf=pdf if str(pdf).lower().endswith(".pdf") else "",
                    apply_link="https://ssc.gov.in/",
                    verification_source="official:ssc.gov.in",
                    tags="ssc,central,exam"))
        except Exception:
            pass
    return out


def rrb():
    page = soup("https://rrb.indianrailways.gov.in/")
    if page is None:
        return []
    out = []
    for a in page.select("a[href]"):
        t = clean(a.get_text())
        low = t.lower()
        if len(t) < 10 or "cen" not in low and "recruitment" not in low:
            continue
        href = a["href"]
        url = href if href.startswith("http") else "https://rrb.indianrailways.gov.in/" + href.lstrip("/")
        out.append(Notification(
            job_name=f"RRB: {t}"[:180], organization="Railway Recruitment Boards",
            department="Ministry of Railways", category="Job",
            state="All India", location="All India (zone choice incl. Bengaluru)",
            official_website="https://rrb.indianrailways.gov.in/",
            apply_link="https://www.rrbapply.gov.in",
            official_pdf=url if url.lower().endswith(".pdf") else "",
            verification_source="official:rrb.indianrailways.gov.in",
            tags="rrb,railway,central"))
    return out


def ibps():
    page = soup("https://www.ibps.in/")
    if page is None:
        return []
    out = []
    for a in page.select("a[href]"):
        t = clean(a.get_text())
        low = t.lower()
        if len(t) < 12:
            continue
        if not any(k in low for k in ("crp", "recruitment", "notification", "vacanc")):
            continue
        href = a["href"]
        url = href if href.startswith("http") else "https://www.ibps.in/" + href.lstrip("/")
        out.append(Notification(
            job_name=f"IBPS: {t}"[:180], organization="IBPS",
            department="Institute of Banking Personnel Selection", category="Exam",
            state="All India", location="All India",
            official_website="https://www.ibps.in/",
            apply_link=url,
            official_pdf=url if url.lower().endswith(".pdf") else "",
            verification_source="official:ibps.in",
            tags="ibps,banking,central"))
    return out


def agnipath_vayu():
    page = soup("https://agnipathvayu.cdac.in/AV/")
    if page is None:
        return []
    out = []
    text = clean(page.get_text(" "))
    for m in re.finditer(r"(AGNIVEER\s*VAYU[^.|]{0,80}INTAKE\s*0?\d/\d{4})", text, re.I):
        out.append(Notification(
            job_name=clean(m.group(1)).title()[:180],
            organization="Indian Air Force (CASB)",
            department="Ministry of Defence", category="Job",
            state="All India", location="All India",
            official_website="https://agnipathvayu.cdac.in/AV/",
            apply_link="https://agnipathvayu.cdac.in/AV/",
            verification_source="official:agnipathvayu.cdac.in",
            tags="defence,air force,agniveer,central"))
    return out


def employment_news():
    page = soup("https://www.employmentnews.gov.in/")
    if page is None:
        return []
    out = []
    for a in page.select("a[href]"):
        t = clean(a.get_text())
        if len(t) < 20:
            continue
        low = t.lower()
        if not any(k in low for k in ("recruitment", "vacanc", "posts", "notification")):
            continue
        href = a["href"]
        url = href if href.startswith("http") else "https://www.employmentnews.gov.in/" + href.lstrip("/")
        out.append(Notification(
            job_name=t[:180], organization="Employment News listing",
            department="", category="Job", state="All India", location="",
            official_website="https://www.employmentnews.gov.in/",
            apply_link=url,
            verification_source="official:employmentnews.gov.in",
            tags="employment news,central"))
    return out
