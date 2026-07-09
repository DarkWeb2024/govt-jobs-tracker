# Configuration

Two layers: `config/config.yaml` (behaviour, no secrets) and environment
variables or a `.env` file in the project root (secrets). Copy `.env.example`
to `.env` to start. `.env` is git-ignored.

## config.yaml sections

- `owner` - your identity, used in reports
- `paths` - database, reports, site and log locations
- `filters` - qualifications, branches, exclude keywords, max experience,
  allowed states, tracked keywords. Add or remove keywords freely; the pipeline
  reads this file on every run.
- `email`, `mstodo`, `whatsapp` - per-channel enable flags and options
- `sources` - turn individual scrapers on/off

## Email (Gmail, free)

1. Google Account -> Security -> 2-Step Verification (enable it)
2. https://myaccount.google.com/apppasswords -> create app password "tracker"
3. In `.env`:
   ```
   TRACKER_SMTP_USER=fairozkhanofficial@gmail.com
   TRACKER_SMTP_PASS=<16-char app password>
   ```
The daily email goes to `email.to` in config.yaml at the end of every run,
with PDF, CSV and Excel attached.

## Microsoft To Do (Graph API, free)

1. https://entra.microsoft.com -> App registrations -> New registration
   - Name: govt-jobs-tracker
   - Supported accounts: "Personal Microsoft accounts only"
   - No redirect URI needed
2. Copy the Application (client) ID into `.env` as `TRACKER_MS_CLIENT_ID`
3. In the app: API permissions -> add delegated permission `Tasks.ReadWrite`
4. Authentication -> Allow public client flows -> Yes
5. Run `python main.py --login-mstodo` and follow the device-code prompt once.

Tokens are cached in `data/ms_token_cache.json` (git-ignored). Only VERIFIED
notifications are ever synced. Lists created: Verified Jobs, Verified Exams,
Applied Jobs, Applied Exams, Deadlines.

## WhatsApp (free options)

Default: CallMeBot (self-message service).
1. Save +34 644 66 32 62 as a contact
2. Send it the WhatsApp message: "I allow callmebot to send me messages"
3. Put the API key you receive in `.env`:
   ```
   TRACKER_CALLMEBOT_PHONE=91xxxxxxxxxx
   TRACKER_CALLMEBOT_APIKEY=xxxxx
   ```
4. Set `whatsapp.enabled: true` in config.yaml.

Alternative: Meta WhatsApp Cloud API free tier - create a Meta developer app,
add the WhatsApp product, use the test number and a permanent token; wire it in
`src/notify/whatsapp.py` (a `provider` switch is already in config). CallMeBot
is simpler and enough for self-alerts.

## GitHub Actions secrets

Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:
`TRACKER_SMTP_USER`, `TRACKER_SMTP_PASS`, `TRACKER_MS_CLIENT_ID`,
`TRACKER_CALLMEBOT_PHONE`, `TRACKER_CALLMEBOT_APIKEY`. Any missing secret just
disables that channel for cloud runs.
