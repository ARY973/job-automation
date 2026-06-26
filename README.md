# Job Automation System — Phase 1
## Aryan Mudhole | Career Automation Pipeline

---

## What This Does

Every Monday morning, this pipeline automatically:
1. Scrapes LinkedIn Jobs across 14 target locations
2. Filters out senior roles, sponsorship blockers, and excluded industries
3. Checks H1B sponsorship history for each company
4. Scores each role 1-10 based on fit
5. Outputs top 15 vetted roles for your review

---

## Files

| File | Purpose |
|------|---------|
| `job_scraper.py` | Main scraper — Apify + filtering + scoring |
| `sheet_logger.py` | Logs results to Google Sheet tracker |
| `resume_matcher.py` | Matches JD to best resume variant |
| `weekly_runner.sh` | Runs full pipeline in one command |

---

## Target Locations

**Utah (Priority 1):**
- Salt Lake City, UT
- Provo / Lehi / Lindon, UT

**National Tier 1 (Priority 2):**
- Austin, TX | Denver, CO | Seattle, WA | Dallas, TX | Atlanta, GA

**National Tier 2 (Priority 3):**
- Chicago, IL | Phoenix, AZ | Minneapolis, MN | Raleigh, NC

**Remote:** United States (all remote DA roles)

---

## Filters

**Auto-Remove (Deal Breakers):**
- Title contains: Senior, Sr., Lead, Principal, Manager, Director
- Description contains: "no sponsorship", "security clearance", "5+ years"
- Industry: Defense, Oil & Gas, Government

**Must Have (At Least One):**
- Title contains: Data Analyst, Business Intelligence, BI Analyst,
  Analytics Engineer, Data Engineer, Product Analyst, AI Analyst

---

## Scoring System (1-10)

| Factor | Points |
|--------|--------|
| Utah location | +2 |
| Remote role | +1 |
| Known H1B sponsor | +2 |
| Priority 1 location | +1 |
| Key skills in JD | +1 to +3 |
| Entry level signals | +1 |
| Preferred industry | +1 |
| No sponsorship mention | -3 |

---

## Resume Variants

| Variant | Best For |
|---------|---------|
| v5 (Base) | General DA, reporting, insights roles |
| USU_BI | BI/dashboard, Power BI, governance roles |
| Grit | ETL/pipeline, API integration, data engineering |
| Deloitte | Cloud, Snowflake, data engineering, consulting |

---

## Weekly Workflow

```
Monday — Automated
  Run: bash weekly_runner.sh
  Output: Top 15 vetted roles in Google Sheet

Tuesday — You (15 min)
  Open Google Sheet
  Review top roles
  Pick 3-5 to apply this week

Per Application — Semi-Automated
  Paste JD to Claude
  Claude identifies best resume variant
  Claude builds tailored resume (2 min)
  Claude builds cover letter (2 min)
  You apply + log in tracker
```

---

## Setup

1. Set environment variables:
   ```
   export APIFY_TOKEN=your_token
   ```

2. Run manually:
   ```
   python3 job_scraper.py
   ```

3. Set up weekly cron (optional):
   ```
   0 9 * * 1 cd /path/to/job_automation && bash weekly_runner.sh
   ```

---

## Google Sheet Tracker
https://docs.google.com/spreadsheets/d/1HNxlJ_vIHZl5XWYlYl_RbvtyEfNsLbYbXpCSuzparMU
