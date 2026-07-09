# Government Jobs & Exams Intelligence Tracker

Automated daily tracker for Indian government jobs and exams. It scrapes official
government sources every night, verifies each notification against official domains,
stores everything in SQLite with full change history, and publishes:

- a live website (GitHub Pages, dark theme, search/filters/countdowns/bookmarks)
- CSV / Excel / PDF / JSON / Markdown reports
- an RSS feed
- a daily summary email with attachments
- Microsoft To Do lists (verified notifications only)
- optional WhatsApp deadline alerts

Scope: Central Government, PSUs, government banks, defence, research institutes,
government exams, apprenticeships - plus Karnataka state government. Other states
are filtered out. Eligibility focus: 10th/12th/Diploma/ITI/graduate/B.E-B.Tech
(AI/ML/CSE/ISE/ECE/EEE/Mech/Civil), freshers, max 2 years experience.

Everything runs on free services: GitHub Actions + GitHub Pages, Gmail SMTP,
Microsoft Graph free tier, CallMeBot for WhatsApp.

## Quick start (Windows)

```powershell
git clone https://github.com/Darkweb2024/govt-jobs-tracker
cd govt-jobs-tracker
powershell -ExecutionPolicy Bypass -File install.ps1
```

That installs dependencies, runs the first pipeline pass (seeds ~25 curated
notifications and scrapes all sources), and registers a Windows Task Scheduler
job at 11:40 PM daily. Cloud automation via GitHub Actions runs at the same time
independently - see docs/DEPLOYMENT.md.

## Daily flow

```
scrape official sources -> filter (eligibility/location/spam) -> verify against
official domains -> dedup + change history (SQLite) -> priority engine ->
outputs (site, CSV, Excel, PDF, JSON, MD, RSS) -> email / To Do / WhatsApp
```

## Verification rules

- Official domain + official PDF: "Verified with Official PDF" (confidence 0.9+)
- Official website listing: "Verified with Official Website" (0.85)
- Aggregator find with an official link attached: "Verified with Official Notification" (0.7)
- Aggregator only: "Unverified" (0.3) - never trusted, never synced to To Do
- Past deadline: "Application Closed"

## CLI

```
python main.py                     full daily run
python main.py --list-urgent      deadlines within 7 days
python main.py --status <id> "Applied"    update your application status
python main.py --login-mstodo     one-time Microsoft To Do login
```

## Documentation

| Doc | Contents |
|-----|----------|
| docs-src/INSTALLATION.md | step-by-step setup, all platforms |
| docs-src/CONFIGURATION.md | config.yaml, secrets, email/To Do/WhatsApp setup |
| docs-src/ARCHITECTURE.md | design, data flow, folder structure |
| docs-src/DEPLOYMENT.md | GitHub Actions, Pages, Task Scheduler, cron |
| docs-src/TROUBLESHOOTING.md | common failures and fixes |
| docs-src/USER_MANUAL.md | using the site, reports and statuses |
| docs-src/DEVELOPER_MANUAL.md | adding scrapers, module API, data schema |
| docs-src/SECURITY.md | secret handling, what never gets committed |
| docs-src/BACKUP.md | what to back up and how to restore |

## Honest limitations

- ssc.gov.in and a few portals render client-side; when their APIs answer nothing,
  coverage comes from other official sources and aggregators (marked Unverified).
- X/LinkedIn/Telegram scraping is not implemented: there is no free, compliant API
  for it. The official-first source list makes this a minor loss.
- Always open the official notification PDF before paying any application fee.
