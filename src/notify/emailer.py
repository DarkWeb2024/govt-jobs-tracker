"""Daily summary email via Gmail SMTP (free, needs an app password)."""
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ..logger import get_logger

log = get_logger("email")


def _summary_html(notifications, changes):
    urgent = sorted([n for n in notifications
                     if n.days_left() is not None and 0 <= n.days_left() <= 7],
                    key=lambda n: n.days_left())
    fresh = sorted(notifications, key=lambda n: n.first_seen, reverse=True)[:10]
    from ..models import is_applied
    applied = [n for n in notifications if is_applied(n.status)]
    unverified = [n for n in notifications if n.verification_status == "Unverified"]

    def rows(items, extra=lambda n: ""):
        if not items:
            return "<tr><td colspan='3' style='color:#888'>Nothing today</td></tr>"
        return "".join(
            f"<tr><td><a href='{n.apply_link or n.official_website}'>{n.job_name}</a></td>"
            f"<td>{n.application_end or 'TBA'}</td><td>{extra(n)}</td></tr>"
            for n in items)

    style = ("<style>body{font-family:Arial,sans-serif;color:#222}"
             "table{border-collapse:collapse;width:100%;margin:8px 0 18px}"
             "td,th{border:1px solid #ddd;padding:6px;font-size:13px;text-align:left}"
             "th{background:#1F4E78;color:#fff}h2{color:#1F4E78;font-size:16px}</style>")
    return f"""<html><head>{style}</head><body>
<h1 style="color:#1F4E78">Govt Jobs Daily Summary - {datetime.now():%d %b %Y}</h1>
<p>Tracked: {len(notifications)} | Urgent (7 days): {len(urgent)} |
Applied: {len(applied)} | Unverified: {len(unverified)} |
Changes in 24h: {len(changes or [])}</p>
<h2>Deadlines within 7 days</h2>
<table><tr><th>Notification</th><th>Last date</th><th>Days left</th></tr>
{rows(urgent, lambda n: str(n.days_left()))}</table>
<h2>Newest notifications</h2>
<table><tr><th>Notification</th><th>Last date</th><th>Verification</th></tr>
{rows(fresh, lambda n: n.verification_status)}</table>
<h2>Your applications</h2>
<table><tr><th>Notification</th><th>Last date</th><th>Status</th></tr>
{rows(applied, lambda n: n.status)}</table>
<p style="color:#888;font-size:12px">Full data: PDF/CSV/Excel attached.
Unverified items need official confirmation before you pay any fee.</p>
</body></html>"""


def send_daily(cfg, notifications, changes, attachments):
    if not cfg["email"]["enabled"]:
        log.info("email disabled in config")
        return False
    user = os.environ.get("TRACKER_SMTP_USER")
    pw = os.environ.get("TRACKER_SMTP_PASS")
    if not user or not pw:
        log.warning("TRACKER_SMTP_USER / TRACKER_SMTP_PASS not set - skipping email. "
                    "See docs-src/CONFIGURATION.md for the 2-minute Gmail app password setup.")
        return False
    msg = MIMEMultipart()
    msg["Subject"] = f"Govt Jobs Daily - {datetime.now():%d %b %Y}"
    msg["From"] = user
    msg["To"] = cfg["email"]["to"]
    msg.attach(MIMEText(_summary_html(notifications, changes), "html"))
    for path in attachments:
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(path))
            part["Content-Disposition"] = f'attachment; filename="{os.path.basename(path)}"'
            msg.attach(part)
    try:
        with smtplib.SMTP(cfg["email"]["smtp_host"], cfg["email"]["smtp_port"]) as s:
            s.starttls()
            s.login(user, pw)
            s.send_message(msg)
        log.info("daily email sent to %s", cfg["email"]["to"])
        return True
    except Exception as e:
        log.error("email failed: %s", e)
        return False
