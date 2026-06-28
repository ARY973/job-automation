"""
Google Sheets Auto-Logger  (v3 — targets the v2 tracker + dedup)
================================================================
Reads the latest results_*.json produced by job_scraper.py and APPENDS
only previously-unseen jobs to Aryan's "Job Application Tracker v2".

Runs unattended inside GitHub Actions via a Google service account (gspread).

Required environment variables (set as GitHub Secrets):
    GOOGLE_SERVICE_ACCOUNT_JSON  - the full service-account JSON
    GOOGLE_SHEET_ID              - optional; defaults to the v2 tracker below

Dedup: a job is "already seen" if its title|company|location matches a row
already in the sheet. Only genuinely new jobs are appended. (The v2 sheet has
no Link column, so we key on title+company+location rather than URL.)
"""

import os
import re
import glob
import json
import sys
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

# Use the env var only if non-empty; an unset GitHub secret injects "".
# Default = "Aryan Mudhole — Job Application Tracker v2".
SHEET_ID = os.getenv("GOOGLE_SHEET_ID") or "1Di3HzjEVzTUmFJb4a8S0cOSdOgsdBZYAHS_2Uwh5kcA"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

# v2 column layout (order matters — appended rows must line up under these).
HEADERS = ["Date Applied", "Company", "Role Title", "Location", "Market",
           "Industry", "Source", "Sponsorship", "Resume Version",
           "Cover Letter", "Application Status", "Response Date",
           "Notes", "Next Action", "Link"]

# 0-based column indices used to identify an existing row.
COMPANY_COL = 1   # Company
ROLE_COL = 2      # Role Title
LOCATION_COL = 3  # Location


# ── helpers ───────────────────────────────────────────────────────────────────
def _key(title, company, location):
    base = f"{title}|{company}|{location}".lower()
    return re.sub(r"\s+", " ", base).strip()


def job_key(job):
    return _key(job.get("title", ""), job.get("company", ""), job.get("location", ""))


def row_key(row):
    role = row[ROLE_COL] if len(row) > ROLE_COL else ""
    company = row[COMPANY_COL] if len(row) > COMPANY_COL else ""
    location = row[LOCATION_COL] if len(row) > LOCATION_COL else ""
    return _key(role, company, location)


def format_row(job):
    """Format a job result (results_*.json) as a v2 Sheets row (14 cols)."""
    score = job.get("score", 0)
    note_bits = [f"Score: {score}/10"]
    if job.get("key_match"):
        note_bits.append(job["key_match"])
    return [
        job.get("date_found") or datetime.now().strftime("%m/%d/%Y"),  # Date Applied
        job.get("company", ""),                                        # Company
        job.get("title", ""),                                          # Role Title
        job.get("location", ""),                                       # Location
        job.get("market", ""),                                         # Market
        "",                                                            # Industry (manual)
        job.get("platform", "LinkedIn"),                              # Source
        job.get("sponsorship", "Unknown"),                           # Sponsorship
        job.get("resume", "PM_Universal"),                           # Resume Version
        "",                                                           # Cover Letter (manual)
        "Not Applied",                                                # Application Status
        "",                                                           # Response Date
        " | ".join(note_bits),                                        # Notes
        f"Apply: {job.get('apply', 'Maybe')}",                       # Next Action
        job.get("link", ""),                                          # Link
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
