"""Shared HTTP fetch helpers for all scrapers."""
import time

import requests
import urllib3
from bs4 import BeautifulSoup

from ..logger import get_logger

log = get_logger("scraping")

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept-Language": "en-IN,en;q=0.9",
}


def fetch(url, retries=2, timeout=25, allow_insecure_fallback=True):
    """GET a URL with retries. Some Indian govt portals ship incomplete
    certificate chains; for those we retry once without verification and
    log it, rather than losing the source."""
    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.SSLError as e:
            last_err = e
            if allow_insecure_fallback:
                log.warning("SSL verify failed for %s - retrying unverified", url)
                try:
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                    r = requests.get(url, headers=HEADERS, timeout=timeout, verify=False)
                    r.raise_for_status()
                    return r
                except Exception as e2:
                    last_err = e2
        except Exception as e:
            last_err = e
        time.sleep(2 * (attempt + 1))
    log.error("fetch failed: %s (%s)", url, last_err)
    return None


def soup(url, **kw):
    r = fetch(url, **kw)
    return BeautifulSoup(r.text, "lxml") if r is not None else None


def clean(s):
    return " ".join((s or "").split())
