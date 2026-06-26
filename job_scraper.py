"""
CJA Job Automation — Phase 1 v2: Multi-Platform Job Discovery
=============================================================
Uses openclawai/job-board-scraper to scrape LinkedIn, Indeed,
Glassdoor, Google Jobs, and ZipRecruiter simultaneously.

Weekly automated pipeline:
1. Scrapes 5 platforms x 14 locations
2. Filters by level, keywords, deal breakers
3. Checks H1B sponsorship history
4. Scores each role 1-10
5. Outputs top 15 vetted roles

Requires env: APIFY_TOKEN=your_token
"""

import os
import json
import time
import requests
from datetime import datetime

APIFY_TOKEN = os.getenv('APIFY_TOKEN')
ACTOR = "openclawai~job-board-scraper"

SEARCHES = [
    {"location": "Salt Lake City, UT",  "term": "Data Analyst",                 "priority": 1},
    {"location": "Salt Lake City, UT",  "term": "Business Intelligence Analyst", "priority": 1},
    {"location": "Lehi, UT",            "term": "Data Analyst",                 "priority": 1},
    {"location": "Salt Lake City, UT",  "term": "Analytics Engineer",           "priority": 1},
    {"location": "Austin, TX",          "term": "Data Analyst",                 "priority": 2},
    {"location": "Denver, CO",          "term": "Data Analyst",                 "priority": 2},
    {"location": "Seattle, WA",         "term": "Data Analyst",                 "priority": 2},
    {"location": "Dallas, TX",          "term": "Data Analyst",                 "priority": 2},
    {"location": "Atlanta, GA",         "term": "Data Analyst",                 "priority": 2},
    {"location": "Chicago, IL",         "term": "Data Analyst",                 "priority": 3},
    {"location": "Phoenix, AZ",         "term": "Data Analyst",                 "priority": 3},
    {"location": "Minneapolis, MN",     "term": "Data Analyst",                 "priority": 3},
    {"location": "Raleigh, NC",         "term": "Data Analyst",                 "priority": 3},
    {"location": "Remote",              "term": "Data Analyst Remote",          "priority": 2},
]

PLATFORMS = ["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"]

DEALBREAKER_TITLE = [
    "senior", "sr.", "sr ", "lead", "principal", "manager",
    "director", "head of", "vp ", "vice president", "chief", "architect"
]

DEALBREAKER_DESC = [
    "no sponsorship", "visa sponsorship is not available",
    "us citizenship required", "security clearance", "top secret",
    "5+ years", "7+ years", "8+ years", "10+ years"
]

AVOID_COMPANIES = [
    "lockheed", "raytheon", "northrop", "general dynamics",
    "l3harris", "booz allen", "saic", "leidos",
    "halliburton", "chevron", "exxon", "shell"
]

MUST_HAVE_TITLE = [
    "data analyst", "business intelligence", "bi analyst",
    "analytics engineer", "data engineer", "reporting analyst",
    "data scientist", "ai analyst", "product analyst",
    "operations analyst", "business analyst"
]

GOOD_SKILLS = [
    "power bi", "python", "sql", "tableau", "etl", "pipeline",
    "machine learning", "databricks", "snowflake", "dbt",
    "analytics", "dashboard", "visualization", "pandas"
]

def check_sponsorship(company):
    if not company:
        return "Unknown"
    try:
        clean = company.lower().strip()
        for word in [",", ".", "inc", "llc", "ltd", "corp"]:
            clean = clean.replace(word, "")
        url = f"https://h1bdata.info/index.php?em={requests.utils.quote(clean.strip())}&job=data+analyst&city=&year=2024"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200 and len(resp.text) > 2000:
            return "Yes"
        return "Unknown"
    except:
        return "Unknown"

def score_job(job, sponsorship, priority):
    score = 5
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    company = (job.get("company") or job.get("companyName") or "").lower()
    location = (job.get("location") or "").lower()

    if any(x in location for x in ["utah", "salt lake", "provo", "lehi", "logan"]):
        score += 2
    elif "remote" in location or "remote" in title:
        score += 1

    if sponsorship == "Yes":
        score += 2
    elif sponsorship == "No":
        score -= 3

    if priority == 1:
        score += 1

    matches = sum(1 for s in GOOD_SKILLS if s in desc)
    score += min(matches, 3)

    entry = ["entry level", "junior", "associate", "0-2 years", "1-3 years"]
    if any(e in desc or e in title for e in entry):
        score += 1

    good = ["saas", "fintech", "healthcare", "edtech", "tech", "software", "university"]
    if any(g in company or g in desc for g in good):
        score += 1

    return min(max(score, 1), 10)

def passes_filter(job):
    title = (job.get("title") or "").lower()
    desc = (job.get("description") or "").lower()
    company = (job.get("company") or job.get("companyName") or "").lower()

    if not any(k in title for k in MUST_HAVE_TITLE):
        return False
    if any(b in title for b in DEALBREAKER_TITLE):
        return False
    if any(b in desc for b in DEALBREAKER_DESC):
        return False
    if any(a in company for a in AVOID_COMPANIES):
        return False
    return True

def run_scraper(search, max_results=15):
    print(f"   Scraping: {search['term']} in {search['location']}...")
    headers = {"Authorization": f"Bearer {APIFY_TOKEN}"}
    run_url = f"https://api.apify.com/v2/acts/{ACTOR}/runs"

    payload = {
        "searchTerm": search["term"],
        "location": search["location"],
        "sites": PLATFORMS,
        "maxResults": max_results,
        "jobType": "fulltime",
        "hoursOld": 168,
        "countryIndeed": "usa",
        "descriptionFormat": "markdown",
        "enforceAnnualSalary": True,
        "linkedinFetchDescription": True,
        "proxyConfiguration": {"useApifyProxy": True}
    }

    try:
        resp = requests.post(run_url, json=payload, headers=headers, timeout=30)
        if resp.status_code not in (200, 201):
            print(f"   Failed: {resp.status_code}")
            return []

        run_id = resp.json()["data"]["id"]
        dataset_id = resp.json()["data"]["defaultDatasetId"]

        for _ in range(24):
            time.sleep(5)
            status_resp = requests.get(
                f"https://api.apify.com/v2/acts/{ACTOR}/runs/{run_id}",
                headers=headers, timeout=10
            )
            status = status_resp.json()["data"]["status"]
            if status in ("SUCCEEDED", "FAILED", "ABORTED"):
                break

        if status != "SUCCEEDED":
            print(f"   Run ended: {status}")
            return []

        items_resp = requests.get(
            f"https://api.apify.com/v2/datasets/{dataset_id}/items?format=json",
            headers=headers, timeout=30
        )
        jobs = items_resp.json()
        print(f"   Found: {len(jobs)} raw results")
        return jobs

    except Exception as e:
        print(f"   Error: {e}")
        return []

def run_pipeline():
    print(f"\n{'='*60}")
    print(f"JOB AUTOMATION v2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Platforms: LinkedIn + Indeed + Glassdoor + Google + ZipRecruiter")
    print(f"{'='*60}\n")

    all_jobs = []
    seen = set()

    for search in SEARCHES:
        jobs = run_scraper(search)
        for job in jobs:
            job_id = (
                job.get("id") or
                f"{job.get('title','')}-{job.get('company','')}-{job.get('location','')}"
            )
            if job_id in seen:
                continue
            seen.add(job_id)

            if not passes_filter(job):
                continue

            company = job.get("company") or job.get("companyName") or ""
            sponsorship = check_sponsorship(company)
            score = score_job(job, sponsorship, search["priority"])

            job["_sponsorship"] = sponsorship
            job["_score"] = score
            job["_search_location"] = search["location"]
            job["_platform"] = job.get("source") or job.get("platform") or "Unknown"
            all_jobs.append(job)

        time.sleep(3)

    all_jobs.sort(key=lambda x: x["_score"], reverse=True)
    top_jobs = all_jobs[:15]

    print(f"\n{'='*60}")
    print(f"TOP {len(top_jobs)} VETTED ROLES THIS WEEK")
    print(f"{'='*60}\n")

    results = []
    for i, job in enumerate(top_jobs, 1):
        title = job.get("title", "N/A")
        company = job.get("company") or job.get("companyName", "N/A")
        location = job.get("location", "N/A")
        salary = job.get("salary") or job.get("salaryMin") or "Not listed"
        platform = job.get("_platform", "Unknown")
        link = job.get("jobUrl") or job.get("link") or job.get("applyUrl", "N/A")
        score = job["_score"]
        sponsorship = job["_sponsorship"]

        print(f"{i:2}. [{score}/10] {title}")
        print(f"    {company} | {location}")
        print(f"    Salary: {salary} | Platform: {platform}")
        print(f"    Sponsorship: {sponsorship}")
        print(f"    {link}\n")

        results.append({
            "score": score,
            "title": title,
            "company": company,
            "location": location,
            "salary": str(salary),
            "platform": platform,
            "sponsorship": sponsorship,
            "link": link,
            "date_found": datetime.now().strftime("%Y-%m-%d"),
        })

    output = f"results_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)

    print(f"✅ {len(top_jobs)} vetted roles saved to {output}")
    print(f"📊 Tracker: https://docs.google.com/spreadsheets/d/1HNxlJ_vIHZl5XWYlYl_RbvtyEfNsLbYbXpCSuzparMU")
    return results

if __name__ == "__main__":
    run_pipeline()
