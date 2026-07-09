# Security

## Secrets

- All secrets live in environment variables or `.env` (git-ignored). The repo
  and config.yaml never contain passwords, tokens or API keys.
- Gmail: use an app password, never the account password. Revoke it anytime at
  myaccount.google.com/apppasswords without affecting the account.
- Microsoft: the Graph token cache (`data/ms_token_cache.json`) is git-ignored;
  it grants only `Tasks.ReadWrite` (To Do lists), nothing else.
- GitHub Actions secrets are encrypted by GitHub and only exposed to the
  workflow at runtime.

## What the system sends and where

- Email: summary + reports to the configured address only.
- Microsoft To Do: notification titles, dates and official links to your own
  account.
- WhatsApp (CallMeBot): a short daily text to your own number. CallMeBot is a
  third-party relay - it sees the message text (job titles and dates, nothing
  personal). If that is unacceptable, use the Meta Cloud API option instead.

## Scraping posture

- Public listing pages only, one fetch per source per day, honest User-Agent
  string, retries capped at 2. No logins, no paywalls, no personal data.
- The unverified-SSL fallback applies only to reading public government pages
  with broken certificate chains; nothing sensitive is transmitted.

## Repo hygiene

- `.gitignore` blocks `.env`, `logs/`, token caches, `__pycache__`.
- The published site contains only public recruitment data.
- If a secret ever lands in a commit: rotate it first, then rewrite history
  (`git filter-repo`) - rotation matters more than the rewrite.
