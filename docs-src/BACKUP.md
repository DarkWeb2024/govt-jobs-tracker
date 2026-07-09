# Backup and Restore

## What matters

| Item | Why | Where it already is |
|------|-----|---------------------|
| data/tracker.db | all records, statuses, history | committed to GitHub daily |
| data/seed.json | first-run bootstrap | in the repo |
| config/config.yaml | your filters and settings | in the repo |
| .env | secrets | NOT in the repo - back up privately |
| Reports/Archive | daily CSV snapshots | committed by the Actions run |

Because the GitHub Actions workflow commits the database and reports back to
the repository every night, GitHub itself is the primary backup, with full
history (`git log -- data/tracker.db`).

## Manual backup

```powershell
Copy-Item data\tracker.db "backup\tracker_$(Get-Date -Format yyyy-MM-dd).db"
```

Keep a private copy of `.env` in your password manager - it is the only file
that cannot be regenerated from the repo.

## Restore

1. Fresh clone.
2. Recreate `.env` from your password manager.
3. Nothing else: the database arrives with the clone; the next run continues
   the history. If the database were ever lost entirely, seed.json rebuilds a
   working baseline and scrapers refill current notifications on first run
   (past history would be gone, statuses would need re-marking).

## Rollback

The daily commit gives point-in-time recovery:

```bash
git log --oneline -- data/tracker.db      # find the good day
git checkout <commit> -- data/tracker.db
git commit -m "Restore database to <date>"
```
