# Troubleshooting

Logs live in `logs/` (pipeline.log, scraping.log, email.log, mstodo.log,
whatsapp.log, database.log). Read the newest lines first.

## A source returns 0 items

Normal for ssc.gov.in (client-side app; its API answers intermittently) and
employmentnews.gov.in (unstable). The run is not an error - other sources and
the aggregator cover the gap. If isro/kea/judiciary return 0 repeatedly, the
site layout changed: see docs-src/DEVELOPER_MANUAL.md on fixing a scraper.

## SSL certificate errors in scraping.log

Several Indian government portals ship incomplete certificate chains. base.py
retries once without verification and logs a warning. This is deliberate and
limited to fetching public listings.

## Email not sending

- "TRACKER_SMTP_USER / TRACKER_SMTP_PASS not set": create `.env` (CONFIGURATION.md)
- "Username and Password not accepted": you used the account password; Gmail
  needs an app password, which needs 2-Step Verification on.
- Attachment too large is never an issue here (reports are < 1 MB).

## Microsoft To Do not syncing

- "no Microsoft account logged in": run `python main.py --login-mstodo`
- AADSTS error about public client: enable "Allow public client flows" in the
  app registration (Authentication tab).
- Token expired after long inactivity: delete data/ms_token_cache.json and
  log in again.

## WhatsApp silent

CallMeBot free tier occasionally throttles. The pipeline treats it as
best-effort: check whatsapp.log; re-send the "I allow callmebot..." message if
the key was revoked.

## GitHub Actions run failed

Open the run log in the Actions tab. The usual causes:
- push rejected: someone pushed manually in between; re-run the workflow
- a scraper crash shows the module name in the log; sources are isolated, one
  failing source never kills the run (it is caught and counted in errors)

## Duplicates appeared

Two records for one notification means neither carried an advertisement number
and titles differed. Merge manually: note both ids from data.json, keep one via
`python main.py --status <bad-id> "Cancelled"`, and add the advt number pattern
to models.make_id if it is a recurring format.

## Windows task did not run

- PC was asleep at 23:40: with StartWhenAvailable it fires on next wake/boot.
- Check history: Task Scheduler -> GovtJobsTracker -> History tab.
