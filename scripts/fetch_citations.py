#!/usr/bin/env python3
"""Fetch per-paper citation counts from Google Scholar and write citations.json.

Run manually with `python scripts/fetch_citations.py`, or let the
"Update Google Scholar citations" GitHub Action run it on a schedule.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from scholarly import scholarly

SCHOLAR_AUTHOR_ID = "0wlIglwAAAAJ"
ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = ROOT / "index.html"
OUTPUT_PATH = ROOT / "citations.json"

# Site title -> Google Scholar title, for the rare paper whose title on
# Scholar hasn't caught up with the (possibly renamed) working paper on
# the site.
TITLE_ALIASES = {
    "Timing is Everything: Estimating Strategic Responses with Observational Data":
        "Estimating Strategic Response in Sequential Data",
}


def normalize(title: str) -> str:
    title = title.lower()
    title = re.sub(r"[^a-z0-9\s]", "", title)
    return re.sub(r"\s+", " ", title).strip()


def site_paper_titles() -> list[str]:
    html = INDEX_HTML.read_text(encoding="utf-8")
    return re.findall(r'<div class="paper-title">(.*?)</div>', html)


def main() -> int:
    site_titles = site_paper_titles()

    author = scholarly.search_author_id(SCHOLAR_AUTHOR_ID)
    author = scholarly.fill(author, sections=["publications"])

    scholar_by_norm = {}
    for pub in author.get("publications", []):
        title = pub.get("bib", {}).get("title")
        if not title:
            continue
        scholar_by_norm[normalize(title)] = pub.get("num_citations", 0)

    papers = []
    unmatched = []
    for site_title in site_titles:
        lookup_title = TITLE_ALIASES.get(site_title, site_title)
        citations = scholar_by_norm.get(normalize(lookup_title))
        if citations is None:
            unmatched.append(site_title)
            continue
        papers.append({"title": site_title, "citations": citations})

    if unmatched:
        print(f"Warning: no Scholar match for: {unmatched}", file=sys.stderr)

    if not papers:
        print("No citation data fetched; leaving citations.json untouched", file=sys.stderr)
        return 1

    data = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scholar_profile": f"https://scholar.google.com/citations?user={SCHOLAR_AUTHOR_ID}&hl=en",
        "papers": papers,
    }
    OUTPUT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(papers)} paper citation counts to {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
