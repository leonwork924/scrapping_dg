#!/usr/bin/env python3
"""
Sponsor Radar - IND Public Register of Recognised Sponsors scraper.

Scrapes the Dutch IND's public register(s) of recognised sponsors,
diffs against the previous run, and writes JSON consumed by the
static site in /site.

Source (fully public, no login, no subscription required):
  https://ind.nl/en/public-register-recognised-sponsors

The IND states the register is updated once a month. This script is
idempotent: running it more often than that simply produces an empty
diff until the source actually changes.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
# Data lives inside site/ so the whole "site" folder can be deployed as a
# single static root on Vercel (matching the existing site/*.json pattern).
DATA_DIR = ROOT / "site" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; SponsorRadarBot/1.0; "
        "+https://github.com/leonwork924/sponsor-radar) "
        "Low-frequency research bot reading only the public register."
    ),
    "Accept-Language": "en",
}

REQUEST_TIMEOUT = 60
MIN_EXPECTED_ROWS = 500  # sanity check: IND lists thousands of sponsors

# Category -> IND public register URL. "work" covers labour +
# highly skilled migrant sponsors, the category Jeroen asked about.
CATEGORIES = {
    "work": "https://ind.nl/en/public-register-recognised-sponsors/public-register-work",
    "exchange": "https://ind.nl/en/public-register-recognised-sponsors/public-register-exchange",
    "study": "https://ind.nl/en/public-register-recognised-sponsors/public-register-study",
    "research": "https://ind.nl/en/public-register-recognised-sponsors/public-register-research",
}

UPDATED_RE = re.compile(
    r"last updated on\s+([0-9]{1,2}\s+\w+\s+[0-9]{4})", re.IGNORECASE
)


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def parse_register(html: str) -> tuple[list[dict], str | None]:
    """Parse one IND public-register page into a list of
    {"organisation": ..., "kvk": ...} dicts, plus the source's own
    'last updated' date string if present on the page."""
    soup = BeautifulSoup(html, "lxml")

    updated_match = UPDATED_RE.search(soup.get_text(" ", strip=True))
    last_updated = updated_match.group(1) if updated_match else None

    table = soup.find("table")
    if table is None:
        raise RuntimeError(
            "No <table> found on the page - IND may have changed their "
            "markup. Inspect the page manually before re-running."
        )

    rows: list[dict] = []
    seen = set()
    for tr in table.find_all("tr"):
        cells = [c.get_text(strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        org, kvk = cells[0].strip(), cells[1].strip()
        if org.lower().startswith("organisation") or kvk.lower().startswith("kvk"):
            continue  # header row
        if not org or not kvk:
            continue
        key = (org, kvk)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"organisation": org, "kvk": kvk})

    if len(rows) < MIN_EXPECTED_ROWS:
        print(
            f"  WARNING: only {len(rows)} rows parsed - IND may paginate "
            "this page or have changed their markup. Verify manually "
            "before trusting the diff.",
            file=sys.stderr,
        )

    return rows, last_updated


def load_previous(category: str) -> dict | None:
    path = DATA_DIR / f"sponsors_{category}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def save_current(category: str, payload: dict) -> None:
    path = DATA_DIR / f"sponsors_{category}.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def diff_new_entries(previous: dict | None, current_rows: list[dict]) -> list[dict]:
    """Newly added organisations = present now, absent from the
    previous snapshot (keyed on KVK number, the stable identifier)."""
    if previous is None:
        return []  # first run: this becomes the baseline, not "new leads"
    previous_kvks = {r["kvk"] for r in previous["organisations"]}
    return [r for r in current_rows if r["kvk"] not in previous_kvks]


def run() -> None:
    all_new: dict[str, dict] = {}
    run_started = datetime.now(timezone.utc).isoformat()

    for category, url in CATEGORIES.items():
        print(f"Scraping category '{category}' from {url} ...")
        html = fetch(url)
        rows, source_last_updated = parse_register(html)
        previous = load_previous(category)
        is_baseline = previous is None
        new_entries = diff_new_entries(previous, rows)

        payload = {
            "category": category,
            "source_url": url,
            "source_last_updated": source_last_updated,
            "scraped_at": run_started,
            "count": len(rows),
            "organisations": rows,
        }
        save_current(category, payload)

        all_new[category] = {
            "source_last_updated": source_last_updated,
            "is_baseline": is_baseline,
            "new_count": 0 if is_baseline else len(new_entries),
            "new_organisations": [] if is_baseline else new_entries,
        }

        status = "baseline seeded" if is_baseline else f"{len(new_entries)} new"
        print(
            f"  -> {len(rows)} organisations total ({status}), "
            f"source last updated: {source_last_updated}"
        )

    new_sponsors_path = DATA_DIR / "new_sponsors.json"
    new_sponsors_path.write_text(
        json.dumps(
            {"generated_at": run_started, "categories": all_new},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {new_sponsors_path}")


if __name__ == "__main__":
    run()
