"""Verification: only official government domains can mark a record verified."""
import json
import os
from datetime import datetime
from urllib.parse import urlparse

OFFICIAL_SUFFIXES = (".gov.in", ".nic.in", ".ac.in", ".res.in", ".mil.in")
OFFICIAL_DOMAINS = {
    "ibps.in", "www.ibps.in", "ibpsonline.ibps.in", "ibpsreg.ibps.in",
    "sbi.bank.in", "sbi.co.in", "www.sbi.co.in",
    "iocl.com", "www.iocl.com", "licindia.in", "www.licindia.in",
    "hal-india.co.in", "bel-india.in", "bemlindia.in",
    "agnipathvayu.cdac.in", "joinindiannavy.gov.in", "joinindianarmy.nic.in",
    "rrbapply.gov.in",
}

ORG_REGISTRY = "data/organizations.json"


def _load_registry_domains():
    """Every domain in the master organization registry counts as official."""
    if not os.path.exists(ORG_REGISTRY):
        return
    try:
        with open(ORG_REGISTRY, encoding="utf-8") as f:
            orgs = json.load(f).get("organizations", [])
    except (OSError, ValueError):
        return
    for org in orgs:
        for url in (org.get("website"), org.get("careers")):
            if url:
                host = urlparse(url).netloc.lower()
                if host:
                    OFFICIAL_DOMAINS.add(host)
                    OFFICIAL_DOMAINS.add(host.removeprefix("www."))


_load_registry_domains()


def is_official(url):
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    return host in OFFICIAL_DOMAINS or host.endswith(OFFICIAL_SUFFIXES)


def apply(n):
    """Set verification status + confidence from the record's own evidence."""
    now = datetime.now().isoformat(timespec="seconds")
    n.verification_timestamp = now
    pdf_official = is_official(n.official_pdf) and n.official_pdf.lower().endswith(".pdf")
    site_official = is_official(n.official_website) or is_official(n.apply_link)

    if pdf_official and site_official:
        n.verification_status = "Verified with Official PDF"
        n.confidence = 0.95
    elif pdf_official:
        n.verification_status = "Verified with Official PDF"
        n.confidence = 0.9
    elif site_official and n.verification_source.startswith("official:"):
        n.verification_status = "Verified with Official Website"
        n.confidence = 0.85
    elif site_official:
        # official link known but data came from an aggregator
        n.verification_status = "Verified with Official Notification"
        n.confidence = 0.7
    else:
        n.verification_status = "Unverified"
        n.confidence = 0.3
    dl = n.days_left()
    if dl is not None and dl < 0:
        n.verification_status = "Application Closed"
    return n
