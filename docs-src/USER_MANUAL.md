# User Manual

## The website

https://darkweb2024.github.io/govt-jobs-tracker/ (refreshed nightly)

- Search box matches name, organization, qualification and tags.
- Filters: category (Job/Exam/Apprenticeship), verification, priority.
- "Open only" hides closed/expired records (on by default).
- Star icon bookmarks a card (stored in your browser).
- "Mark applied" tracks your applications in the browser; "My applications"
  shows them plus anything marked Applied in the database itself.
- Countdown colors: red = 3 days or less, amber = 7 or less, green = later.
- Export buttons download the latest CSV/Excel/PDF/JSON; RSS for feed readers.

## Reading verification labels

| Label | Meaning | Safe to pay a fee? |
|-------|---------|--------------------|
| Verified with Official PDF | official domain + official PDF on file | Yes, after reading the PDF |
| Verified with Official Website | listed on the official portal itself | Yes, read the notification first |
| Verified with Official Notification | aggregator find with official link | Open the official link first |
| Unverified | aggregator only | No - wait for official confirmation |
| Application Closed / Expired | deadline passed | Do not apply |

## Tracking your applications (database-level)

Find the notification id on the website (data.json) or in the CSV, then:

```
python main.py --status <id> "Applied"
python main.py --status <id> "Admit Card Available"
python main.py --status <id> "Result Declared"
```

Allowed statuses: Not Applied, Applied, Application Submitted, Fee Pending,
Fee Paid, Exam Scheduled, Admit Card Available, Exam Completed, Answer Key
Released, Result Awaited, Result Declared, Interview, Document Verification,
Offer Released, Rejected, Completed, Already Applied.

Status changes are protected - the nightly scrape never overwrites them - and
they flow into the email, PDF, Excel Applied sheet and Microsoft To Do.

## Merging duplicates (official vs aggregator naming)

The same recruitment sometimes arrives twice - once from the official site,
once from a job portal with a different headline. When you have manually
confirmed both are the same, keep the official one:

```
python main.py --merge <official_id> <duplicate_id>
```

What happens: the official record absorbs anything the duplicate knew that it
did not (vacancies, dates, links), an Applied status carries over, the
duplicate is deleted, and its id is remembered as an alias - so tomorrow's
scrape of the portal updates the official record instead of resurrecting the
duplicate. Find both ids in the CSV export or docs/data.json (the site's
search box helps locate the pair).

For records that are simply noise (not duplicates), use the site's
"Not interested" button or `--status <id> "Not Interested"` instead.

## Updates on applied jobs and exams

Every nightly run watches all sources for announcements that mention your
applied records - admit cards, hall tickets, results, answer keys, merit
lists, correction windows, exam dates, interview schedules, cut-offs. A match
is stamped into the record's notes with the date and link, appears in the
site card, in the Excel History sheet, and in the "changes" section of the
daily email. Nothing is overwritten automatically - when you actually download
an admit card, promote the status yourself:

```
python main.py --status <id> "Admit Card Available"
```

## The daily email

Arrives after the 23:40 run: counts, deadlines within 7 days, newest finds,
your applications, with PDF/CSV/Excel attached.

## Reports on disk

- Reports/Daily: JSON + Markdown per day
- Reports/CSV, Reports/Excel, Reports/PDF: dated full exports
- Reports/Weekly (Sundays), Reports/Monthly (1st), Reports/Archive: snapshots
