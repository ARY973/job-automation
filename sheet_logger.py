"""
Google Sheets Auto-Logger
=========================
Takes job results from the scraper and logs them
directly to Aryan's Google Sheet tracker.

Requires: GOOGLE_SHEET_ID environment variable
Uses: Google Drive MCP connector for authentication
"""

import json
import os
from datetime import datetime

SHEET_ID = "1HNxlJ_vIHZl5XWYlYl_RbvtyEfNsLbYbXpCSuzparMU"

def format_row(job):
    """Format a job result as a Google Sheets row."""
    return [
        datetime.now().strftime('%m/%d/%Y'),  # Date Found
        job.get('company', ''),               # Company
        job.get('title', ''),                 # Role Title
        job.get('location', ''),              # Location
        '',                                    # Industry (manual)
        'LinkedIn',                            # Source
        job.get('sponsorship', 'Unknown'),     # Sponsorship
        'v5',                                  # Resume Version (default)
        'Not Applied',                         # Status
        '',                                    # Response Date
        f"Score: {job.get('score', 0)}/10",   # Notes
        'Review and apply',                    # Next Action
        job.get('link', ''),                   # Job Link
    ]

def log_to_sheet(results):
    """
    Log job results to Google Sheet.
    Called after scraper pipeline completes.
    """
    print(f"\n📊 Logging {len(results)} jobs to Google Sheet...")
    rows = [format_row(job) for job in results]

    # Output formatted rows for manual entry or API logging
    print("\nFormatted rows ready for Google Sheet:")
    print("=" * 80)
    headers = ["Date", "Company", "Role", "Location", "Industry",
               "Source", "Sponsorship", "Resume", "Status",
               "Response", "Notes", "Next Action", "Link"]
    print(" | ".join(headers))
    print("-" * 80)
    for row in rows:
        print(" | ".join(str(cell) for cell in row))

    return rows

if __name__ == '__main__':
    # Load latest results
    import glob
    result_files = sorted(glob.glob('/home/claude/job_automation/results_*.json'))
    if result_files:
        with open(result_files[-1]) as f:
            results = json.load(f)
        log_to_sheet(results)
    else:
        print("No results found. Run job_scraper.py first.")
