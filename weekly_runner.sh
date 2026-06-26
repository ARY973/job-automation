#!/bin/bash
# ============================================================
# CJA Job Automation — Weekly Runner
# ============================================================
# Run every Monday morning:
# 0 9 * * 1 cd /path/to/job_automation && bash weekly_runner.sh
# ============================================================

echo "🚀 Starting weekly job automation pipeline..."
echo "Date: $(date)"

# Step 1 — Run scraper
echo ""
echo "📥 Step 1: Scraping LinkedIn jobs..."
python3 job_scraper.py

# Step 2 — Log to sheet
echo ""
echo "📊 Step 2: Logging to Google Sheet..."
python3 sheet_logger.py

echo ""
echo "✅ Pipeline complete!"
echo "👉 Review your Google Sheet and pick 3-5 roles to apply to this week"
echo "👉 For each role: paste JD to Claude → get tailored resume → apply"
echo ""
echo "Sheet: https://docs.google.com/spreadsheets/d/1HNxlJ_vIHZl5XWYlYl_RbvtyEfNsLbYbXpCSuzparMU"
