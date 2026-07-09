# Developer Manual

## Adding a scraper

1. Create `src/scrapers/<name>.py` exposing `scrape() -> list[Notification]`.
   Use helpers from `base.py` (`fetch`, `soup`, `clean`); they handle retries,
   UA headers and the broken-cert fallback some government portals need.
2. Fill as many Notification fields as the source offers. Rules:
   - `verification_source`: `"official:<domain>"` for official sites,
     `"aggregator:<domain>"` otherwise - verification depends on it.
   - dates as ISO `YYYY-MM-DD` strings; anything else stays free text and is
     simply excluded from countdowns.
   - do not set `status`, `priority`, `verification_status`, `confidence`;
     the pipeline computes them.
3. Register it in `src/scrapers/registry.py` and add a flag under `sources:`
   in config.yaml.
4. Test in isolation:
   ```python
   python -c "from src.scrapers.<name> import scrape; rs=scrape(); print(len(rs)); print(rs[0].to_dict() if rs else '')"
   ```

A scraper that raises is caught by the pipeline and counted in `errors`; it can
never break the run.

## Data schema (SQLite)

- `notifications(notification_id PK, data JSON, created_at, updated_at)` -
  the record itself lives in the JSON column, mirroring models.Notification.
- `history(notification_id, changed_at, field, old_value, new_value)` -
  one row per changed field per run; feeds the "Changes" report sections.
- `runs(started_at, finished_at, new_count, updated_count, error_count, summary)`

Identity: models.make_id() prefers an advertisement-number pattern
(`XX:00:YYYY`, `CEN 02/2026`, `HCRB/DEA-6/2026`, ...) found in job_name+notes;
otherwise a normalized title+organization hash. Improving that regex is the
main lever against duplicates.

## Module API

- `pipeline.run(cfg_path) -> str summary` - the whole daily cycle
- `database.Store.upsert(n) -> "new"|"updated"|"unchanged"`
- `database.Store.set_status(id, status, note="") -> bool` (history-logged)
- `filters.passes(n, cfg) -> bool` (relevance, spam, experience, location, quals)
- `verify.apply(n) -> n` and `priority.assign(n) -> n` (both mutate + return)
- outputs: `write_csv/json/markdown/rss`, `excel_out.write_excel`,
  `pdf_out.write_pdf`, `website.build_site`
- notify: `emailer.send_daily`, `mstodo.sync`, `whatsapp.send` - each degrades
  to a logged skip when its credentials are absent.

## Conventions

- Python 3.10+, stdlib logging via `logger.get_logger`
- no network calls at import time; scrapers only touch the network in scrape()
- keep scraper output deterministic: sort or de-dup within the module if the
  page repeats links
- run `python main.py` before committing scraper changes; the run must finish
  with `errors=0` unless the source itself is down
