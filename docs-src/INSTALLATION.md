# Installation

## Requirements

- Python 3.10 or newer
- Git
- Windows 10/11, Linux or macOS (scheduler examples cover all three)

## Windows (one command)

```powershell
git clone https://github.com/Darkweb2024/govt-jobs-tracker
cd govt-jobs-tracker
powershell -ExecutionPolicy Bypass -File install.ps1
```

install.ps1 does three things:
1. `pip install -r requirements.txt`
2. runs `python main.py` once (seeds the database, scrapes all sources, builds
   every output under `Reports/` and the website under `docs/`)
3. registers a Windows Task Scheduler job named `GovtJobsTracker` at 23:40 daily
   (with `StartWhenAvailable`, so a missed run fires on next boot)

## Linux / macOS

```bash
git clone https://github.com/Darkweb2024/govt-jobs-tracker
cd govt-jobs-tracker
pip install -r requirements.txt
python main.py
crontab -e     # add: 40 23 * * * cd /path/to/govt-jobs-tracker && python main.py
```

## Verify the install

```bash
python main.py --list-urgent
```

should print notifications closing within 7 days. Check that `Reports/PDF/`,
`Reports/CSV/`, `Reports/Excel/` and `docs/data.json` exist.

## Optional integrations

Email, Microsoft To Do and WhatsApp need one-time credentials that only you can
create (they are free). Follow docs-src/CONFIGURATION.md. The pipeline runs fine
without them and logs a clear skip message for each.
