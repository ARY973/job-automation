"""
Fast end-to-end test of the Sheet write path (no scraping). ~15s.
Confirms the service account can open AND write to the Sheet.
Appends one obvious TEST row you can delete.
"""
import os
import json
import sys

import gspread
from google.oauth2.service_account import Credentials

# Use the env var only if non-empty; an unset GitHub secret injects "".
SHEET_ID = os.getenv("GOOGLE_SHEET_ID") or "1HNxlJ_vIHZl5XWYlYl_RbvtyEfNsLbYbXpCSuzparMU"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]

raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if not raw:
    print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON not set")
    sys.exit(1)

info = json.loads(raw)
print("SA email :", info.get("client_email"))
print("SHEET_ID :", SHEET_ID)

creds = Credentials.from_service_account_info(info, scopes=SCOPES)
client = gspread.authorize(creds)

ws = client.open_by_key(SHEET_ID).sheet1
print("OK - opened worksheet:", ws.title)
print("Existing rows:", len(ws.get_all_values()))

ws.append_row(["TEST WRITE - safe to delete", "ci-check"],
              value_input_option="USER_ENTERED")
print("OK - append succeeded. Sheet write works end to end.")
