"""Microsoft To Do sync via Graph API (free personal Microsoft account).

One-time setup: register a free app in Entra ID, put its client id in the
TRACKER_MS_CLIENT_ID env var, then run `python main.py --login-mstodo` and
follow the device-code prompt. The token cache keeps future runs silent.
Only VERIFIED notifications are synced, per design."""
import json
import os

import requests

from ..logger import get_logger

log = get_logger("mstodo")

GRAPH = "https://graph.microsoft.com/v1.0"
SCOPES = ["Tasks.ReadWrite"]
CACHE = "data/ms_token_cache.json"


def _app():
    import msal
    client_id = os.environ.get("TRACKER_MS_CLIENT_ID")
    if not client_id:
        return None
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE):
        cache.deserialize(open(CACHE, encoding="utf-8").read())
    app = msal.PublicClientApplication(
        client_id, authority="https://login.microsoftonline.com/consumers",
        token_cache=cache)
    return app, cache


def _save(cache):
    if cache.has_state_changed:
        os.makedirs("data", exist_ok=True)
        open(CACHE, "w", encoding="utf-8").write(cache.serialize())


def login_interactive():
    pair = _app()
    if not pair:
        print("Set TRACKER_MS_CLIENT_ID first (docs-src/CONFIGURATION.md).")
        return False
    app, cache = pair
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(flow["message"])  # user visits microsoft.com/devicelogin with the code
    result = app.acquire_token_by_device_flow(flow)
    _save(cache)
    ok = "access_token" in result
    print("Login OK - token cached." if ok else f"Login failed: {result.get('error_description')}")
    return ok


def _token():
    pair = _app()
    if not pair:
        return None
    app, cache = pair
    accounts = app.get_accounts()
    if not accounts:
        log.warning("no Microsoft account logged in - run: python main.py --login-mstodo")
        return None
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    _save(cache)
    return result.get("access_token") if result else None


def _headers(tok):
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


def _ensure_list(tok, name):
    r = requests.get(f"{GRAPH}/me/todo/lists", headers=_headers(tok), timeout=20)
    r.raise_for_status()
    for lst in r.json().get("value", []):
        if lst["displayName"] == name:
            return lst["id"]
    r = requests.post(f"{GRAPH}/me/todo/lists", headers=_headers(tok),
                      json={"displayName": name}, timeout=20)
    r.raise_for_status()
    return r.json()["id"]


def _existing_titles(tok, list_id):
    titles, url = set(), f"{GRAPH}/me/todo/lists/{list_id}/tasks?$top=100"
    while url:
        r = requests.get(url, headers=_headers(tok), timeout=20)
        r.raise_for_status()
        j = r.json()
        titles |= {t["title"] for t in j.get("value", [])}
        url = j.get("@odata.nextLink")
    return titles


def sync(cfg, notifications):
    if not cfg["mstodo"]["enabled"]:
        return 0
    tok = _token()
    if not tok:
        return 0
    lists = cfg["mstodo"]["lists"]
    verified = [n for n in notifications if n.verification_status.startswith("Verified")]
    from ..models import is_applied
    applied = [n for n in notifications if is_applied(n.status)]
    buckets = {
        lists["verified_jobs"]: [n for n in verified if n.category != "Exam"],
        lists["verified_exams"]: [n for n in verified if n.category == "Exam"],
        lists["applied_jobs"]: [n for n in applied if n.category != "Exam"],
        lists["applied_exams"]: [n for n in applied if n.category == "Exam"],
        lists["deadlines"]: [n for n in verified
                             if n.days_left() is not None and 0 <= n.days_left() <= 7],
    }
    created = 0
    try:
        for list_name, items in buckets.items():
            if not items:
                continue
            lid = _ensure_list(tok, list_name)
            existing = _existing_titles(tok, lid)
            for n in items:
                title = f"{n.job_name} [{n.notification_id}]"
                if title in existing:
                    continue
                body = {"title": title,
                        "body": {"content": f"Last date: {n.application_end or 'TBA'}\n"
                                            f"{n.apply_link or n.official_website}",
                                 "contentType": "text"}}
                d = n.end_date()
                if d:
                    body["dueDateTime"] = {"dateTime": f"{d.isoformat()}T18:00:00",
                                           "timeZone": "India Standard Time"}
                requests.post(f"{GRAPH}/me/todo/lists/{lid}/tasks",
                              headers=_headers(tok), json=body, timeout=20).raise_for_status()
                created += 1
        log.info("Microsoft To Do: %d tasks created", created)
    except Exception as e:
        log.error("Microsoft To Do sync failed: %s", e)
    return created
