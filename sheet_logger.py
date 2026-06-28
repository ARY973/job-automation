"""
Google Sheets Auto-Logger  (v2 — real writes + dedup)
=====================================================
Reads the latest results_*.json produced by job_scraper.py and APPENDS
only previously-unseen jobs to Aryan's Google Sheet tracker.

Runs unattended inside GitHub Actions. Because MCP/connectors are NOT
available in CI, this uses a Google service account via gspread.

Required environment variables (set as GitHub Secrets):
    GOOGLE_SERVICE_ACCOUNT_JSON  - the full service-account JSON (paste contents)
    GOOGLE_SHEET_ID              - optional; defaults to the tracker below

Dedup logic:
    A job is "already seen" if its Link matches a Link already in the sheet.
    For rows whose link is missing/N/A, we fall back to a
    title|company|location key. Only new jobs are appended.
"""

import os
import re
import glob
import json
import sys
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1HNxlJ_vIHZl5XWYlYl_RbvtyEfNsLbYbXpCSuzparMU")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = ["Date", "Company", "Role", "Location", "Industry",
           "Source", "Sponsorship", "Resume", "Status",
           "Response", "Notes", "Next Action", "Link"]

# Column index (0-based) of the Link column, used as the dedup key.
LINK_COL = HEADERS.index("Link")


# ── helpers ───────────────────────────────────────────────────────────────────
def _norm_link(link):
    """Normalize a job URL for comparison (strip query string, trailing slash)."""
    if not link:
        return ""
    link = str(link).strip().lower()
    if link in ("n/a", "na", "none", "-"):
        return ""
    link = link.split("?")[0].rstrip("/")
    return link


def _fallback_key(title, company, location):
    """Used when a job has no usable link."""
    base = f"{title}|{company}|{location}".lower()
    return re.sub(r"\s+", " ", base).strip()


def job_key(job):
    """Stable identity for a job dict from results_*.json."""
    link = _norm_link(job.get("link", ""))
    if link:
        return link
    return _fallback_key(job.get("title", ""), job.get("company", ""),
                         job.get("location", ""))


def row_key(row):
    """Stable identity for an existing sheet row (list of cell strings)."""
    link = _norm_link(row[LINK_COL] if len(row) > LINK_COL else "")
    if link:
        return link
    title    = row[2] if len(row) > 2 else ""   # Role
    company  = row[1] if len(row) > 1 else ""   # Company
    location = row[3] if len(row) > 3 else ""   # Location
    return _fallback_key(title, company, location)


def format_row(job):
    """Format a job result (from results_*.json) as a Google Sheets row."""
    score = job.get("score", 0)
    note_bits = [f"Score: {score}/10"]
    if job.get("key_match"):
        note_bits.append(job["key_match"])
    return [
        job.get("date_found") or datetime.now().strftime("%m/%d/%Y"),  # Date Found
        job.get("company", ""),                                        # Company
        job.get("title", ""),                                          # Role Title
        job.get("location", ""),                                       # Location
        "",                                                            # Industry (manual)
        job.get("platform", "LinkedIn"),                              # Source
        job.get("sponsorship", "Unknown"),                           # Sponsorship
        job.get("resume", "PM_Universal"),                           # Resume Version
        "Not Applied",                                                # Status
        "",                                                           # Response Date
        " | ".join(note_bits),                                        # Notes
        f"Apply: {job.get('apply', 'Maybe')}",                       # Next Action
        job.get("link", ""),                                          # Job Link
    ]


def _get_worksheet():
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not raw:
        print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON is not set. Cannot write to the Sheet.")
        sys.exit(1)
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1


def log_to_sheet(results):
    ws = _get_worksheet()
    existing = ws.get_all_values()

    # Ensure a header row exists.
    if not existing:
        ws.append_row(HEADERS, value_input_option="USER_ENTERED")
        existing = [HEADERS]

    seen = {row_key(r) for r in existing[1:]}  # skip header

    new_rows, added_keys = [], set()
    for job in results:
        k = job_key(job)
        if not k or k in seen or k in added_keys:
            continue
        added_keys.add(k)
        new_rows.append(format_row(job))

    if new_rows:
        ws.append_rows(new_rows, value_input_option="USER_ENTERED")

    print(f"Scraped: {len(results)} | New appended: {len(new_rows)} | "
          f"Skipped as duplicates: {len(results) - len(new_rows)}")
    return new_rows


if __name__ == "__main__":
    result_files = sorted(glob.glob("results_*.json"))
    if not result_files:
        print("No results_*.json found. Run job_scraper.py first.")
        sys.exit(0)
    with open(result_files[-1]) as f:
        results = json.load(f)
    log_to_sheet(results)
