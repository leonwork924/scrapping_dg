# Sponsor Radar

Weekly monitor of the Dutch IND's **public register of recognised sponsors**.
Newly listed organisations are strong relocation/mobility leads: a company
just became a recognised sponsor, which means it's now able to bring in
international employees (highly skilled migrants, etc.) and may need
mobility support soon after.

Source: <https://ind.nl/en/public-register-recognised-sponsors> — fully
public, no login, no subscription. The IND publishes it once a month; this
project checks weekly and reports only what's new.

## How it works

1. `scraper/scrape_sponsors.py` fetches the four IND register pages (Work,
   Exchange, Study, Research), parses the Organisation / KVK number table on
   each, and compares it to the previous snapshot.
2. Newly appeared KVK numbers = newly added sponsors. Output goes to
   `site/data/sponsors_<category>.json` (full current list per category) and
   `site/data/new_sponsors.json` (this cycle's diff, all categories).
3. `.github/workflows/scrape.yml` runs the scraper every Monday (and on
   manual trigger) and commits the updated JSON back to the repo.
4. `site/` is a static page that reads that JSON client-side and shows the
   newly added organisations up top, plus a searchable full register below.

The very first run has nothing to diff against, so it seeds the baseline
(`is_baseline: true`, no "new" leads reported) rather than flagging every
existing sponsor as new.

## Setup

```bash
cd scraper
pip install -r requirements.txt
python scrape_sponsors.py
```

This populates `site/data/`. Commit and push that once so the site has data
from the start, then let the GitHub Action take over weekly.

## Deploying

**GitHub:** push this folder to a new repo (`sponsor-radar` or similar).
The Action needs no secrets — it uses the default `GITHUB_TOKEN` with
`contents: write` permission (already set in the workflow) to commit data
updates.

**Vercel:** create a new project from the repo, and in the project's
**Settings → General → Root Directory**, set it to `site`. That's it — it's
a static site (HTML/CSS/vanilla JS), no build step required.

## A note on the parser

The table-parsing logic (`parse_register` in `scrape_sponsors.py`) was
built and unit-tested against the real page's structure (a two-column
Organisation / KVK table with an "overview was last updated on …" line),
using content fetched live from `ind.nl`. It has **not** been run
end-to-end against the live site from within this environment, since
`ind.nl` isn't reachable from here. Before relying on it:

- Run `python scrape_sponsors.py` once locally (or trigger the GitHub
  Action manually via "Run workflow") and check the console output.
- The script prints a warning if it parses fewer than 500 rows for a
  category — that would suggest IND has changed their markup or added
  pagination, and the parser needs adjusting.
- If the site does turn out to be paginated, the fix is localised to
  `parse_register`/`fetch` in `scrape_sponsors.py` — everything downstream
  (diffing, JSON output, site) stays the same.

## Extending

- **Hunter.io enrichment**: once new sponsors are flagged, the same pattern
  used for `agent_corporate_contacts.py` in Tender Radar could enrich each
  new organisation with contact emails before they're reported.
- **Report delivery**: `site/data/new_sponsors.json` is the natural hook for
  a notification step (email digest, Slack message) in the same GitHub
  Actions job, once you decide how you'd like to receive it.
- **Folding into Tender Radar**: this can live as its own repo/site for now,
  or be merged in later as a fifth section alongside Tenders, Newsletter,
  Contact, and Prospection.
