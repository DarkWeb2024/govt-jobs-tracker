"""WhatsApp alerts using CallMeBot - a free self-message gateway.

One-time setup (2 minutes, no payment):
1. Save +34 644 66 32 62 in your phone contacts.
2. WhatsApp the message: "I allow callmebot to send me messages"
3. You receive an API key; set TRACKER_CALLMEBOT_PHONE (with country code,
   e.g. 91xxxxxxxxxx) and TRACKER_CALLMEBOT_APIKEY in the environment.

Meta's WhatsApp Cloud API is the other free-tier option but needs a Meta
Business account; steps are in docs-src/CONFIGURATION.md if you prefer it."""
import os
import urllib.parse

import requests

from ..logger import get_logger

log = get_logger("whatsapp")


def send(cfg, notifications):
    if not cfg["whatsapp"]["enabled"]:
        return False
    phone = os.environ.get("TRACKER_CALLMEBOT_PHONE")
    key = os.environ.get("TRACKER_CALLMEBOT_APIKEY")
    if not phone or not key:
        log.warning("CallMeBot env vars not set - skipping WhatsApp")
        return False
    urgent = sorted([n for n in notifications
                     if n.days_left() is not None and 0 <= n.days_left() <= 3],
                    key=lambda n: n.days_left())
    lines = ["Govt Jobs Tracker daily alert"]
    if urgent:
        lines.append("CRITICAL deadlines:")
        lines += [f"- {n.job_name[:60]} closes {n.application_end} ({n.days_left()}d)"
                  for n in urgent[:5]]
    else:
        lines.append("No deadlines within 3 days.")
    from ..models import is_applied
    applied = [n for n in notifications if is_applied(n.status)]
    lines.append(f"Applications tracked: {len(applied)}")
    msg = urllib.parse.quote("\n".join(lines))
    try:
        r = requests.get(
            f"https://api.callmebot.com/whatsapp.php?phone={phone}&apikey={key}&text={msg}",
            timeout=30)
        ok = r.status_code == 200
        log.info("WhatsApp alert %s", "sent" if ok else f"failed ({r.status_code})")
        return ok
    except Exception as e:
        log.error("WhatsApp failed: %s", e)
        return False
