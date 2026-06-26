"""
Resume Matcher
==============
Given a job description, automatically:
1. Identifies the closest resume variant
2. Lists which bullets to swap
3. Generates tailored summary

Resume Variants Available:
- v5: Base (general DA roles)
- USU_BI: BI/dashboard focused
- Grit: ETL/pipeline focused
- Deloitte: Data engineering focused
"""

import re

RESUME_VARIANTS = {
    "v5": {
        "name": "Base v5",
        "best_for": ["data analyst", "business analyst", "reporting analyst"],
        "keywords": ["analysis", "reporting", "insights", "stakeholder", "kpi"]
    },
    "USU_BI": {
        "name": "USU Business Intelligence",
        "best_for": ["bi analyst", "business intelligence", "dashboard"],
        "keywords": ["power bi", "tableau", "dashboard", "reporting", "institutional",
                     "governance", "data dictionary", "ad-hoc"]
    },
    "Grit": {
        "name": "Grit — Pipeline & Integration",
        "best_for": ["data engineer", "etl", "pipeline", "integration"],
        "keywords": ["etl", "pipeline", "api", "integration", "ingestion",
                     "data quality", "architecture", "scalable"]
    },
    "Deloitte": {
        "name": "Deloitte — Data Engineering",
        "best_for": ["data engineer", "analytics engineer", "cloud"],
        "keywords": ["aws", "snowflake", "databricks", "cloud", "ci/cd",
                     "orchestration", "downstream", "curated datasets"]
    }
}

def match_resume(job_description):
    """
    Given a job description text, return the best resume variant.
    """
    jd_lower = job_description.lower()
    scores = {}

    for variant_id, variant in RESUME_VARIANTS.items():
        score = 0
        for keyword in variant['keywords']:
            if keyword in jd_lower:
                score += 1
        scores[variant_id] = score

    best_variant = max(scores, key=scores.get)
    return best_variant, scores

def analyze_jd(job_description):
    """
    Extract key requirements and suggest tailoring actions.
    """
    jd_lower = job_description.lower()

    # Extract key tools mentioned
    tools = []
    tool_list = ['power bi', 'tableau', 'sql', 'python', 'snowflake', 'databricks',
                 'dbt', 'airflow', 'spark', 'aws', 'azure', 'gcp', 'excel',
                 'looker', 'qlik', 'r ', 'scala', 'java', 'sap', 'salesforce']
    for tool in tool_list:
        if tool in jd_lower:
            tools.append(tool.upper().strip())

    # Check for sponsorship flags
    no_sponsor = any(phrase in jd_lower for phrase in [
        'no sponsorship', 'sponsorship not available',
        'visa sponsorship is not available', 'us citizenship required',
        'must be authorized'
    ])

    # Check experience level
    if any(x in jd_lower for x in ['senior', 'sr.', '5+ years', '7+ years']):
        level = 'Senior — Consider Skipping'
    elif any(x in jd_lower for x in ['entry level', 'junior', '0-2 years', '1-3 years']):
        level = 'Entry/Junior — Strong Target'
    elif '2+ years' in jd_lower or '3+ years' in jd_lower:
        level = 'Mid-Level — Good Target'
    else:
        level = 'Unknown — Review Manually'

    return {
        'tools': tools,
        'no_sponsor_flag': no_sponsor,
        'level': level,
    }

def get_recommendation(job_description, company_name=""):
    """
    Full recommendation for a job posting.
    """
    print(f"\n{'='*60}")
    print(f"RESUME MATCHER ANALYSIS")
    print(f"{'='*60}\n")

    # Match resume
    best_variant, scores = match_resume(job_description)
    analysis = analyze_jd(job_description)

    print(f"Company: {company_name}")
    print(f"Level: {analysis['level']}")
    print(f"Tools mentioned: {', '.join(analysis['tools']) or 'None detected'}")
    print(f"Sponsorship flag: {'🔴 YES — Review carefully' if analysis['no_sponsor_flag'] else '🟢 None detected'}")
    print(f"\nBest resume variant: {RESUME_VARIANTS[best_variant]['name']}")
    print(f"Variant scores: {scores}")
    print(f"\nRecommended action:")

    if analysis['no_sponsor_flag']:
        print("  ⚠️  Sponsorship language detected — verify before applying")
    elif 'Senior' in analysis['level']:
        print("  ⚠️  Senior role — consider skipping unless strong match")
    else:
        print(f"  ✅ Apply with {RESUME_VARIANTS[best_variant]['name']} resume")
        print(f"  ✅ Emphasize: {', '.join(RESUME_VARIANTS[best_variant]['keywords'][:3])}")

    return best_variant, analysis

if __name__ == '__main__':
    # Test with sample JD
    sample_jd = """
    We are looking for a Data Analyst with experience in Power BI,
    SQL, and ETL pipeline development. You will build dashboards and
    reports for stakeholders and work with data governance teams.
    2+ years of experience required.
    """
    get_recommendation(sample_jd, "Sample Company")
