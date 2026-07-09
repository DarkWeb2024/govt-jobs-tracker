# Deployment

## GitHub Pages (the live website)

The pipeline writes the site into `docs/`. In the repository:
Settings -> Pages -> Source: "Deploy from a branch" -> Branch `main`, folder `/docs`.

The site URL becomes https://darkweb2024.github.io/govt-jobs-tracker/

## GitHub Actions (cloud automation, free)

`.github/workflows/daily.yml` runs at 18:10 UTC (= 23:40 IST) every day:
1. installs Python + dependencies
2. runs `python main.py` (scrape, verify, outputs, notifications)
3. commits the refreshed `docs/`, `Reports/` and `data/tracker.db` back to main

Add the five secrets from docs-src/CONFIGURATION.md for email/To Do/WhatsApp in
cloud runs. Trigger manually anytime: Actions tab -> daily-tracker -> Run workflow.

Notes:
- GitHub Actions cron can drift a few minutes under load; that is normal.
- Scheduled workflows are disabled automatically after 60 days without repo
  activity; the daily bot commit keeps it alive.
- The Microsoft To Do token cache is git-ignored, so cloud runs skip To Do
  unless you deliberately provision a cache there. Local runs handle To Do.

## Windows Task Scheduler (local automation)

`install.ps1` registers task `GovtJobsTracker` at 23:40 with StartWhenAvailable.
Manage it: Task Scheduler app, or

```powershell
Get-ScheduledTask GovtJobsTracker | Get-ScheduledTaskInfo
Unregister-ScheduledTask GovtJobsTracker -Confirm:$false   # remove
```

Local and cloud runs coexist: both write the same repo outputs, and the
database dedup makes double-runs harmless.

## Linux cron

```
40 23 * * * cd /opt/govt-jobs-tracker && /usr/bin/python3 main.py >> logs/cron.log 2>&1
```
