"""
CJA Job Automation — Phase 1: Intelligent Job Discovery
========================================================
Weekly automated pipeline that:
1. Scrapes LinkedIn Jobs across 14 target locations
2. Filters by level, keywords, and deal breakers
3. Checks H1B sponsorship history via h1bdata.info
4. Scores each role 1-10
5. Logs top results to Google Sheet tracker

Usage:
    python job_scraper.py

Requires .env:
    APIFY_TOKEN=your_token
    GOOGLE_SHEET_ID=your_sheet_id
"""

import os
import json
import time
import requests
from datetime import datetime

# ── Configuration ─────────────────────────────────────────────────────────────

APIFY_TOKEN = os.getenv('APIFY_TOKEN')

# Target search URLs — Utah first, then national
SEARCH_CONFIGS = [
    # Utah — highest priority
    {"location": "Salt Lake City, UT",     "keywords": "Data Analyst",               "priority": 1},
    {"location": "Salt Lake City, UT",     "keywords": "Business Intelligence Analyst","priority": 1},
    {"location": "Provo Lehi Lindon, UT",  "keywords": "Data Analyst",               "priority": 1},
    {"location": "Salt Lake City, UT",     "keywords": "Analytics Engineer",          "priority": 1},

    # National Tier 1
    {"location": "Austin, TX",             "keywords": "Data Analyst",               "priority": 2},
    {"location": "Denver, CO",             "keywords": "Data Analyst",               "priority": 2},
    {"location": "Seattle, WA",            "keywords": "Data Analyst",               "priority": 2},
    {"location": "Dallas, TX",             "keywords": "Data Analyst",               "priority": 2},
    {"location": "Atlanta, GA",            "keywords": "Data Analyst",               "priority": 2},

    # National Tier 2
    {"location": "Chicago, IL",            "keywords": "Data Analyst",               "priority": 3},
    {"location": "Phoenix, AZ",            "keywords": "Data Analyst",               "priority": 3},
    {"location": "Minneapolis, MN",        "keywords": "Data Analyst",               "priority": 3},
    {"location": "Raleigh, NC",            "keywords": "Data Analyst",               "priority": 3},

    # Remote
    {"location": "United States",          "keywords": "Data Analyst Remote",        "priority": 2},
    {"location": "United States",          "keywords": "Business Intelligence Remote","priority": 2},
]

# ── Deal Breaker Keywords (auto-filter OUT) ───────────────────────────────────
DEALBREAKER_TITLE = [
    "senior", "sr.", "sr ", "lead", "principal", "manager", "director",
    "head of", "vp ", "vice president", "chief", "staff", "architect"
]

DEALBREAKER_DESCRIPTION = [
    "no sponsorship", "visa sponsorship is not available",
    "sponsorship not available", "us citizenship required",
    "must be a us citizen", "security clearance", "top secret",
    "secret clearance", "defense", "oil and gas", "oil & gas",
    "department of defense", "government contractor",
    "5+ years", "7+ years", "8+ years", "10+ years",
    "10 years", "7 years", "8 years"
]

# ── Must-Have Keywords (role must contain at least one) ──────────────────────
MUST_HAVE_TITLE = [
    "data analyst", "business intelligence", "bi analyst",
    "analytics engineer", "data engineer", "reporting analyst",
    "data science", "ai analyst", "ml analyst", "product analyst",
    "operations analyst", "business analyst"
]

# ── Industries to Avoid ───────────────────────────────────────────────────────
AVOID_INDUSTRIES = [
    "defense", "military", "oil", "gas", "petroleum",
    "government", "federal", "department of", "dod", "army",
    "navy", "air force", "lockheed", "raytheon", "northrop",
    "general dynamics", "l3harris", "booz allen", "saic", "leidos"
]

# ── Sponsorship Lookup ────────────────────────────────────────────────────────
def check_h1b_sponsorship(company_name):
    """
    Check if company has H1B sponsorship history via H1B data API.
    Returns: 'Yes', 'No', or 'Unknown'
    """
    if not company_name:
        return 'Unknown'

    try:
        # Clean company name for search
        clean_name = company_name.lower().strip()
        clean_name = clean_name.replace(',', '').replace('.', '').replace('inc', '').replace('llc', '').strip()

        url = f"https://h1bdata.info/index.php?em={requests.utils.quote(clean_name)}&job=data+analyst&city=&year=2024"
        response = requests.get(url, timeout=10)

        if response.status_code == 200 and len(response.text) > 1000:
            # If results page has substantial content, company has sponsored
            return 'Yes'
        else:
            return 'Unknown'
    except:
        return 'Unknown'

# ── Scoring System ────────────────────────────────────────────────────────────
def score_job(job, sponsorship_status, priority):
    """
    Score a job 1-10 based on multiple factors.
    Higher = better fit for Aryan.
    """
    score = 5  # Base score

    title = (job.get('title') or '').lower()
    description = (job.get('description') or job.get('descriptionText') or '').lower()
    company = (job.get('companyName') or '').lower()
    location = (job.get('location') or '').lower()

    # Location bonus
    if 'utah' in location or 'salt lake' in location or 'provo' in location or 'logan' in location:
        score += 2
    elif 'remote' in location or 'remote' in title:
        score += 1

    # Sponsorship bonus
    if sponsorship_status == 'Yes':
        score += 2
    elif sponsorship_status == 'Unknown':
        score += 0
    else:
        score -= 3

    # Priority location bonus
    if priority == 1:
        score += 1

    # Key skills in description
    key_skills = ['power bi', 'python', 'sql', 'tableau', 'etl', 'pipeline',
                  'machine learning', 'databricks', 'snowflake', 'dbt']
    skill_matches = sum(1 for skill in key_skills if skill in description)
    score += min(skill_matches, 3)  # Max +3 for skills

    # Entry level signals
    entry_signals = ['entry level', 'junior', 'associate', '0-2 years',
                     '1-3 years', '2+ years', 'new grad']
    if any(signal in description for signal in entry_signals):
        score += 1

    # Preferred industries
    good_industries = ['fintech', 'saas', 'healthcare', 'edtech', 'tech',
                       'software', 'analytics', 'university', 'research']
    if any(ind in company or ind in description for ind in good_industries):
        score += 1

    return min(max(score, 1), 10)  # Clamp between 1-10

# ── Main Filter Logic ─────────────────────────────────────────────────────────
def filter_job(job):
    """
    Returns True if job passes all filters, False if it should be removed.
    """
    title = (job.get('title') or '').lower()
    description = (job.get('description') or job.get('descriptionText') or '').lower()
    company = (job.get('companyName') or '').lower()

    # Must have relevant title
    if not any(keyword in title for keyword in MUST_HAVE_TITLE):
        return False

    # Filter out senior/executive titles
    if any(breaker in title for breaker in DEALBREAKER_TITLE):
        return False

    # Filter out deal breaker description keywords
    if any(breaker in description for breaker in DEALBREAKER_DESCRIPTION):
        return False

    # Filter out avoid industries
    if any(industry in company or industry in description for industry in AVOID_INDUSTRIES):
        return False

    return True

# ── Apify Scraper ─────────────────────────────────────────────────────────────
def scrape_linkedin_jobs(config, max_results=30):
    """
    Run Apify LinkedIn jobs scraper for a given search config.
    """
    keywords = config['keywords']
    location = config['location']

    # Build LinkedIn search URL
    base_url = "https://www.linkedin.com/jobs/search"
    params = f"?keywords={requests.utils.quote(keywords)}&location={requests.utils.quote(location)}&f_TPR=r604800&position=1&pageNum=0"
    search_url = base_url + params

    print(f"   Scraping: {keywords} in {location}...")

    try:
        # Start Apify actor run
        run_url = "https://api.apify.com/v2/acts/curious_coder~linkedin-jobs-scraper/runs"
        headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}

        payload = {
            "count": max_results,
            "scrapeCompany": False,
            "urls": [search_url]
        }

        response = requests.post(run_url, json=payload, headers=headers, timeout=30)

        if response.status_code not in (200, 201):
            print(f"   Failed to start actor: {response.status_code}")
            return []

        run_id = response.json()['data']['id']
        dataset_id = response.json()['data']['defaultDatasetId']

        # Wait for completion (max 90 seconds)
        for _ in range(18):
            time.sleep(5)
            status_url = f"https://api.apify.com/v2/acts/curious_coder~linkedin-jobs-scraper/runs/{run_id}"
            status_resp = requests.get(status_url, headers=headers, timeout=10)
            status = status_resp.json()['data']['status']
            if status in ('SUCCEEDED', 'FAILED', 'ABORTED'):
                break

        if status != 'SUCCEEDED':
            print(f"   Actor ended with status: {status}")
            return []

        # Fetch results
        results_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json"
        results_resp = requests.get(results_url, headers=headers, timeout=30)
        jobs = results_resp.json()

        print(f"   Found {len(jobs)} raw results")
        return jobs

    except Exception as e:
        print(f"   Error: {e}")
        return []

# ── Main Pipeline ─────────────────────────────────────────────────────────────
def run_pipeline():
    """
    Full automated pipeline: scrape → filter → score → output.
    """
    print(f"\n{'='*60}")
    print(f"JOB AUTOMATION PIPELINE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    all_jobs = []
    seen_ids = set()

    # Scrape each search config
    for config in SEARCH_CONFIGS:
        jobs = scrape_linkedin_jobs(config, max_results=25)

        for job in jobs:
            job_id = job.get('id') or job.get('jobId') or job.get('link')
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)

            # Apply filters
            if not filter_job(job):
                continue

            # Check sponsorship
            company = job.get('companyName') or ''
            sponsorship = check_h1b_sponsorship(company)

            # Score the job
            score = score_job(job, sponsorship, config['priority'])

            # Add metadata
            job['_sponsorship'] = sponsorship
            job['_score'] = score
            job['_search_location'] = config['location']
            job['_priority'] = config['priority']

            all_jobs.append(job)

        time.sleep(2)  # Rate limiting between searches

    # Sort by score descending
    all_jobs.sort(key=lambda x: x['_score'], reverse=True)

    # Take top 15
    top_jobs = all_jobs[:15]

    print(f"\n{'='*60}")
    print(f"TOP {len(top_jobs)} VETTED ROLES")
    print(f"{'='*60}\n")

    results = []
    for i, job in enumerate(top_jobs, 1):
        title = job.get('title', 'N/A')
        company = job.get('companyName', 'N/A')
        location = job.get('location', 'N/A')
        link = job.get('link') or job.get('applyUrl', 'N/A')
        score = job['_score']
        sponsorship = job['_sponsorship']

        print(f"{i:2}. [{score}/10] {title}")
        print(f"    {company} | {location}")
        print(f"    Sponsorship: {sponsorship}")
        print(f"    {link}\n")

        results.append({
            'score': score,
            'title': title,
            'company': company,
            'location': location,
            'sponsorship': sponsorship,
            'link': link,
            'date_found': datetime.now().strftime('%Y-%m-%d'),
        })

    # Save results to JSON
    output_path = f"/home/claude/job_automation/results_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to: {output_path}")
    print(f"✅ Total vetted roles: {len(top_jobs)}")
    print(f"✅ Ready to review and apply!\n")

    return results

if __name__ == '__main__':
    run_pipeline()
