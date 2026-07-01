"""
CJA Job Automation — Phase 2 v4: PM + DA Multi-Platform Discovery
=================================================================
Searches for Product Manager AND Data Analyst roles across
US + India locations on 5 platforms simultaneously.

Requires env:
    APIFY_TOKEN=your_apify_token
    ANTHROPIC_API_KEY=your_claude_api_key
"""

import os
import json
import time
import requests
from datetime import datetime

APIFY_TOKEN       = os.getenv('APIFY_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Local H-1B sponsorship lookup (DOL OFLC LCA FY2025). Degrades gracefully if absent.
try:
    from sponsorship import get_sponsorship as _sponsor_lookup
except Exception:
    _sponsor_lookup = None
ACTOR             = "openclawai~job-board-scraper"
PLATFORMS         = ["linkedin", "indeed", "glassdoor", "google", "zip_recruiter"]

# ── Search Configurations ─────────────────────────────────────────────────────
SEARCHES = [
    # ── US Nationwide — all states; ranking weights H-1B sponsorship strength ──
    {"location": "United States", "term": "Associate Product Manager",  "priority": 1, "market": "US"},
    {"location": "United States", "term": "AI Product Manager",         "priority": 1, "market": "US"},
    {"location": "United States", "term": "Product Analyst",            "priority": 1, "market": "US"},
    {"location": "United States", "term": "Data Product Manager",       "priority": 2, "market": "US"},
    {"location": "United States", "term": "Technical Business Analyst", "priority": 2, "market": "US"},
    {"location": "United States", "term": "Data Analyst",              "priority": 2, "market": "US"},
    {"location": "Remote",        "term": "Associate Product Manager",  "priority": 1, "market": "US"},
    {"location": "Remote",        "term": "AI Product Analyst",         "priority": 2, "market": "US"},

    # ── US Utah — kept for local network advantage (Huntsman alumni, TCI) ──────
    {"location": "Salt Lake City, UT", "term": "Associate Product Manager", "priority": 1, "market": "US"},
    {"location": "Salt Lake City, UT", "term": "Product Analyst",           "priority": 1, "market": "US"},
    {"location": "Lehi, UT",           "term": "Product Manager",           "priority": 1, "market": "US"},

    # ── India — Priority 1 (no visa friction) ─────────────────────────────────
    {"location": "Bangalore, India",    "term": "Associate Product Manager",     "priority": 1, "market": "India"},
    {"location": "Bangalore, India",    "term": "Product Analyst",               "priority": 1, "market": "India"},
    {"location": "Bangalore, India",    "term": "AI Product Manager",            "priority": 1, "market": "India"},
    {"location": "Mumbai, India",       "term": "Associate Product Manager",     "priority": 1, "market": "India"},
    {"location": "Pune, India",         "term": "Associate Product Manager",     "priority": 1, "market": "India"},
    {"location": "Hyderabad, India",    "term": "Product Analyst",               "priority": 1, "market": "India"},

    # ── Canada — Priority 2 ───────────────────────────────────────────────────
    {"location": "Toronto, Canada",     "term": "Associate Product Manager",     "priority": 2, "market": "Canada"},
    {"location": "Vancouver, Canada",   "term": "Product Analyst",               "priority": 2, "market": "Canada"},
]

# ── Filters ───────────────────────────────────────────────────────────────────
DEALBREAKER_TITLE = [
    "senior", "sr.", "sr ", "lead", "principal", "director",
    "head of", "vp ", "vice president", "chief", "staff"
]

DEALBREAKER_DESC = [
    "no sponsorship", "visa sponsorship is not available",
    "us citizenship required", "security clearance", "top secret",
    "7+ years", "8+ years", "10+ years", "10 years experience"
]

AVOID_COMPANIES = [
    "lockheed", "raytheon", "northrop", "general dynamics",
    "l3harris", "booz allen", "saic", "leidos",
    "halliburton", "chevron", "exxon", "shell"
]

MUST_HAVE_TITLE = [
    "product manager", "product analyst", "associate pm", "apm",
    "ai product", "technical product", "data product",
    "business analyst", "product owner", "data analyst",
    "analytics engineer", "ml product", "technical business"
]

GOOD_SKILLS = [
    "python", "sql", "product", "agile", "roadmap", "stakeholder",
    "analytics", "machine learning", "ai", "fintech", "data",
    "etl", "pipeline", "dashboard", "metrics", "kpi"
]

# ── Candidate Profile ─────────────────────────────────────────────────────────
CANDIDATE_PROFILE = """
Name: Aryan (Ryan) Mudhole
Degree: MS Management Information Systems, Utah State University (graduating May 2027)
Work Auth: F-1 OPT (3-year STEM OPT after graduation for US). Indian national (no visa needed for India roles).
Experience:
- Graduate Data Analyst (Product Owner), USU Transforming Communities Institute (Apr 2026-Mar 2027)
  Owned data product end-to-end: requirements gathering, architecture design, pipeline build, production deployment
  Serves 220 clients and Utah Supreme Court reporting goals
- Power BI Analyst Intern, Medikart Pharmaceutical (Jan-Mar 2024)
  Full product discovery to delivery: stakeholder needs → KPI definition → dashboard build → 40% time reduction
- SAP Materials Management Intern, Tata Motors (Jun-Aug 2024)
  Enterprise data systems, procurement analytics at scale
Skills: Python, SQL, ETL pipelines, REST APIs, Power BI, AWS EC2, GitHub Actions,
        XGBoost, Scikit-learn, Advanced ML, LLM integration, data governance
Projects: AI-Powered Stock Trading Pipeline (0-to-1 product build, AWS EC2, XGBoost, Groq Llama 3)
Certs: Databricks Fundamentals Accreditation (100%, Jun 2026)
Leadership: President, USU AI Club
Target roles: Associate PM, AI Product Analyst, Product Analyst, Technical Business Analyst, Data Product Manager
Markets: US (OPT 3yr) + India (citizen, no visa) + Canada
"""

def score_with_claude(job):
    if not ANTHROPIC_API_KEY:
        return {"score": 5, "reasoning": "No API key", "resume_variant": "Razorpay_PM", "apply": "Maybe"}

    title    = job.get("title", "")
    company  = job.get("company") or job.get("companyName", "")
    location = job.get("location", "")
    desc     = (job.get("description") or "")[:3000]
    salary   = job.get("salary") or "Not listed"
    market   = job.get("_market", "US")

    prompt = f"""Analyze this job for the candidate. Return ONLY valid JSON, no other text.

CANDIDATE:
{CANDIDATE_PROFILE}

JOB:
Title: {title}
Company: {company}
Location: {location}
Market: {market}
Salary: {salary}
Description: {desc}

Return ONLY this JSON:
{{
  "score": <1-10 integer>,
  "apply": "<Yes/No/Maybe>",
  "resume_variant": "<PM_Universal/Razorpay_PM/Grit/Deloitte/USU_BI/v5>",
  "sponsorship_flag": <true/false>,
  "key_match": "<strongest match in one sentence>",
  "key_gap": "<biggest gap in one sentence, or None>",
  "reasoning": "<2 sentences max>"
}}

Score guide:
9-10: Excellent fit — title matches target roles, experience level appropriate, strong skill overlap
7-8: Good fit — most requirements match, minor gaps
5-6: Moderate fit — some gaps but worth considering
3-4: Stretch role — significant gaps
1-2: Poor fit — skip

Resume variants:
- PM_Universal: For any PM/product analyst role — leads with product ownership story
- Razorpay_PM: India PM roles specifically
- Grit: ETL/pipeline/data engineering roles
- Deloitte: Cloud/AWS/data engineering consulting
- USU_BI: Power BI/dashboard/BI analyst roles
- v5: General DA roles

India market note: Salary expectations INR 10-20 LPA for entry PM roles. No sponsorship needed."""

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=30
        )
        if resp.status_code == 200:
            text = resp.json()["content"][0]["text"].strip()
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            return json.loads(text)
        return {"score": 5, "reasoning": f"API error {resp.status_code}", "resume_variant": "PM_Universal", "apply": "Maybe"}
    except Exception as e:
        return {"score": 5, "reasoning": str(e), "resume_variant": "PM_Universal", "apply": "Maybe"}

def check_sponsorship(company, market):
    if market == "India":
        return "N/A - India role"
    if market == "Canada":
        return "No lottery - Express Entry"
    # Use the local OFLC LCA lookup: real per-employer H-1B history, role-aware.
    if _sponsor_lookup:
        try:
            summary, _facts = _sponsor_lookup(company or "", "US")
            return summary
        except Exception:
            pass
    return "Unknown"

def passes_filter(job):
    title   = (job.get("title") or "").lower()
    desc    = (job.get("description") or "").lower()
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
    """Scrape via the open-source JobSpy library directly (free, runs in CI).
    Replaces the paid Apify actor — JobSpy is the same engine the actor wrapped."""
    print(f"   [{search['market']}] {search['term']} in {search['location']}...")
    from jobspy import scrape_jobs  # lazy import (keeps module importable without it)
    country = {"US": "USA", "India": "India", "Canada": "Canada"}.get(search["market"], "USA")
    try:
        df = scrape_jobs(
            site_name=PLATFORMS,
            search_term=search["term"],
            google_search_term=f"{search['term']} jobs near {search['location']}",
            location=search["location"],
            results_wanted=max_results,
            hours_old=168,
            country_indeed=country,
            linkedin_fetch_description=True,   # full descriptions + direct apply URLs
        )
        if df is None or len(df) == 0:
            print("   Found: 0")
            return []
        # pandas NaN -> None so downstream `.get(...) or ...` works cleanly.
        df = df.astype(object).where(df.notna(), None)
        jobs = df.to_dict("records")
        print(f"   Found: {len(jobs)} raw results")
        return jobs
    except Exception as e:
        print(f"   Error: {e}")
        return []

def run_pipeline():
    print(f"\n{'='*60}")
    print(f"JOB AUTOMATION v4 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Roles: PM + Product Analyst + DA")
    print(f"Markets: US + India + Canada")
    print(f"Platforms: LinkedIn + Indeed + Glassdoor + Google + ZipRecruiter")
    print(f"{'='*60}\n")

    all_jobs = []
    seen     = set()

    print("Step 1: Scraping jobs across all markets...\n")
    for search in SEARCHES:
        jobs = run_scraper(search)
        for job in jobs:
            # JobSpy uses snake_case: job_url_direct (direct apply), job_url (listing).
            # Keep camelCase fallbacks in case the actor renames fields.
            job["link"] = (
                job.get("job_url_direct") or job.get("job_url") or
                job.get("jobUrl") or job.get("url") or
                job.get("applyUrl") or job.get("externalApplyLink") or "N/A"
            )
            # JobSpy uses "site" for the board name (linkedin/indeed/...).
            job["platform"] = (
                job.get("site") or job.get("source") or job.get("platform") or
                job.get("jobBoard") or "LinkedIn"
            )
            job["_market"] = search["market"]

            job_id = (
                job.get("id") or
                f"{job.get('title','')}-{job.get('company','')}-{job.get('location','')}"
            )
            if job_id in seen:
                continue
            seen.add(job_id)

            if passes_filter(job):
                all_jobs.append((job, search["priority"], search["market"]))
        time.sleep(3)

    print(f"\n{len(all_jobs)} jobs passed filters")

    print(f"\nStep 2: Claude AI scoring {len(all_jobs)} jobs...\n")
    scored = []
    for job, priority, market in all_jobs:
        company     = job.get("company") or job.get("companyName") or ""
        sponsorship = check_sponsorship(company, market)
        claude      = score_with_claude(job)

        score = claude.get("score", 5)
        loc   = (job.get("location") or "").lower()
        sp    = str(sponsorship)

        # ── Sponsorship strength = primary signal for an OPT candidate ────────
        # (US jobs only; India/Canada fall through to the market boost below.)
        if sp.startswith("Strong"):
            score = min(score + 3, 10)
        elif sp.startswith("Moderate"):
            score = min(score + 2, 10)
        elif sp.startswith("Light"):
            score = min(score + 1, 10)
        elif sp.startswith("None"):
            score = max(score - 1, 1)   # US company, no FY25 H-1B history: deprioritize

        # ── Market / location (modest) ────────────────────────────────────────
        if market == "India":
            score = min(score + 2, 10)          # no visa friction
        elif any(x in loc for x in ["utah", "salt lake", "lehi", "provo"]):
            score = min(score + 1, 10)          # local network advantage
        elif "remote" in loc:
            score = min(score + 1, 10)

        if priority == 1:
            score = min(score + 1, 10)

        job["_sponsorship"] = sponsorship
        job["_score"]       = score
        job["_claude"]      = claude
        job["_market"]      = market
        scored.append(job)
        time.sleep(1)

    scored.sort(key=lambda x: x["_score"], reverse=True)
    top = scored[:40]  # Top 40 across all markets (broadened for fall applying)

    print(f"\n{'='*60}")
    print(f"TOP {len(top)} VETTED ROLES THIS WEEK")
    print(f"{'='*60}\n")

    results = []
    for i, job in enumerate(top, 1):
        title   = job.get("title", "N/A")
        company = job.get("company") or job.get("companyName", "N/A")
        loc     = job.get("location", "N/A")
        salary  = job.get("salary") or "Not listed"
        link    = job.get("link", "N/A")
        score   = job["_score"]
        sp      = job["_sponsorship"]
        cl      = job["_claude"]
        market  = job["_market"]

        print(f"{i:2}. [{score}/10] [{market}] {title}")
        print(f"    {company} | {loc}")
        print(f"    Salary: {salary} | Apply: {cl.get('apply','?')} | Resume: {cl.get('resume_variant','PM_Universal')}")
        print(f"    Sponsorship: {sp} | {cl.get('key_match','')}")
        print(f"    {link}\n")

        results.append({
            "score": score,
            "market": market,
            "title": title,
            "company": company,
            "location": loc,
            "salary": str(salary),
            "platform": job.get("platform", "LinkedIn"),
            "sponsorship": sp,
            "link": link,
            "apply": cl.get("apply", "Maybe"),
            "resume": cl.get("resume_variant", "PM_Universal"),
            "key_match": cl.get("key_match", ""),
            "key_gap": cl.get("key_gap", ""),
            "reasoning": cl.get("reasoning", ""),
            "date_found": datetime.now().strftime("%Y-%m-%d"),
            "_claude": cl,
        })

    output = f"results_{datetime.now().strftime('%Y%m%d')}.json"
    with open(output, "w") as f:
        json.dump(results, f, indent=2)

    # Summary by market
    us_count     = sum(1 for r in results if r["market"] == "US")
    india_count  = sum(1 for r in results if r["market"] == "India")
    canada_count = sum(1 for r in results if r["market"] == "Canada")

    print(f"Results by market: US={us_count} | India={india_count} | Canada={canada_count}")
    print(f"Results saved to {output}")
    print(f"\nPipeline complete! Review and pick 3-5 to apply this week.\n")
    return results

if __name__ == "__main__":
    run_pipeline()
