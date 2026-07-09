# Architecture

## Data flow

```
        +--------------------- daily 23:40 IST ----------------------+
        |                                                            |
scrapers (official first)          filters              verification |
 isro.py  karnataka_hc.py   -->  eligibility   -->  official-domain  |
 kea.py   central.py             location           rules + PDF      |
 aggregator.py (last)            spam/nav-noise     confidence score |
        |                                                            |
        v                                                            |
   SQLite store (data/tracker.db)                                    |
   - dedup by advertisement number, else normalized title            |
   - field-level change history                                      |
   - protected fields: status, notes (never overwritten by scrape)   |
        |                                                            |
        v                                                            |
   priority engine (days to deadline: 3/7/30)                        |
        |                                                            |
        +--> outputs: docs/ website + data.json + feed.xml           |
        |            Reports/{CSV,Excel,PDF,Daily,Weekly,Monthly,Archive}
        +--> notify: email (SMTP), Microsoft To Do (Graph), WhatsApp |
```

## Folder structure

```
govt-jobs-tracker/
  main.py               CLI entry point (.env loader, run/status/urgent/login)
  config/config.yaml    behaviour config (no secrets)
  data/seed.json        curated verified notifications loaded on first run
  data/tracker.db       SQLite database (committed so Actions keeps history)
  src/
    models.py           Notification dataclass, status vocabularies, id logic
    database.py         Store: upsert, dedup, history, runs
    filters.py          eligibility/location/spam/nav-noise rules
    verify.py           official-domain verification + confidence
    priority.py         deadline-based priority
    pipeline.py         orchestrator
    logger.py           rotating file + console logs (logs/)
    scrapers/           one module per source + registry
    outputs/            tabular (csv/json/md/rss), excel_out, pdf_out, website
    notify/             emailer, mstodo, whatsapp
  site/index.html       website template (copied to docs/ on each run)
  docs/                 generated site - GitHub Pages serves this
  docs-src/             this documentation
  Reports/              generated reports by type and period
  .github/workflows/daily.yml   cloud automation
  install.ps1           one-command Windows setup
```

## Design decisions

- Official-first sourcing: aggregators only widen the net; they can never mark
  a record verified. verify.py trusts .gov.in/.nic.in/.ac.in/.res.in domains
  plus an explicit allowlist (ibps.in, sbi.bank.in, iocl.com, ...).
- Identity: an advertisement number (e.g. ISTRAC:02:2026, CEN 02/2026) is the
  strongest key; the same notification found on two sites merges into one record.
- The database is the single source of truth; every output is a pure projection
  of it, regenerated fully each run.
- Human-set fields (status, notes) are protected from scraper overwrites.
- Website is static and framework-free: one HTML file plus data.json, so
  GitHub Pages hosts it with zero build step.
