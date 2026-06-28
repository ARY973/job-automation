"""
Fast credential/sheet-access test (no scraping).
Verifies the service account can open and write to the Google Sheet.
Run via the 'Test Sheet Write' workflow (workflow_dispatch). ~30 seconds.
Safe: it appends one obvious TEST row you can delete.
"""
import os
import json
import sys

import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1HNxlJ_vIHZl5XWYlYl_RbvtyEfNsLbYbXpCSuzparMU")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if not raw:
    print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON not set")
    sys.exit(1)

info = json.loads(raw)
print("Service account email:", info.get("client_email"))
print("Project ID:", info.get("project_id"))

creds = Credentials.from_service_account_info(info, scopes=SCOPES)
client = gspread.authorize(creds)

print("Opening sheet by key...")
ws = client.open_by_key(SHEET_ID).sheet1
print("OK - opened worksheet:", ws.title)

rows = ws.get_all_values()
print("Existing rows:", len(rows))

ws.append_row(["TEST WRITE - safe to delete", "ci-check"],
              value_input_option="USER_ENTERED")
print("OK - append succeeded. Sheet write works.")
