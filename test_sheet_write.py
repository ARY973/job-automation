"""
Diagnostic: pinpoint why the Sheets API call returns HTML.
Prints the exact HTTP status + response body so we know if it's
auth (401), permission (403), API-not-enabled, or wrong ID (404).
Run via 'Test Sheet Write' workflow (workflow_dispatch). ~15s, no scraping.
"""
import os
import json
import sys

from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request, AuthorizedSession

SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "1HNxlJ_vIHZl5XWYlYl_RbvtyEfNsLbYbXpCSuzparMU")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
if not raw:
    print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON not set")
    sys.exit(1)

info = json.loads(raw)
print("SA email   :", info.get("client_email"))
print("project_id :", info.get("project_id"))
print("token_uri  :", info.get("token_uri"))
print("SHEET_ID   :", SHEET_ID)
print("-" * 50)

creds = Credentials.from_service_account_info(info, scopes=SCOPES)

# 1) Can we even mint an access token? (catches bad key / clock skew)
try:
    creds.refresh(Request())
    print("Token refresh: OK (token length", len(creds.token or ""), ")")
except Exception as e:
    print("Token refresh FAILED:", repr(e))
    sys.exit(1)

# 2) Hit the Sheets API directly and show the raw status + body.
sess = AuthorizedSession(creds)
url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=properties.title"
r = sess.get(url)
print("HTTP status :", r.status_code)
print("Content-Type:", r.headers.get("content-type"))
print("Body[:800]  :")
print(r.text[:800])
print("-" * 50)
sys.exit(0 if r.status_code == 200 else 2)
