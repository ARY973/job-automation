"""
Sponsorship-strength enrichment from DOL OFLC LCA FY2025 disclosure data.
Looks up an employer's H-1B filing history and returns a concise signal +
structured facts. Built by build_sponsorship_lookup.py; data refreshes quarterly.

US jobs only — India needs no sponsorship, Canada is Express Entry.
"""
import os, re, json, gzip, bisect

_HERE = os.path.dirname(os.path.abspath(__file__))
_SUFFIX = {"inc","llc","ltd","corp","corporation","co","lp","llp","plc","pllc",
           "incorporated","limited","the"}
# Brand -> normalized legal-name prefix, for names that file under an unrelated legal name.
_ALIAS = {"esri":"ENVIRONMENTAL SYSTEMS RESEARCH INSTITUTE", "xai":"X AI"}

_LOOKUP = None
_KEYS = None

def _load():
    global _LOOKUP, _KEYS
    if _LOOKUP is None:
        path = os.path.join(_HERE, "sponsorship_lookup.json.gz")
        if os.path.exists(path):
            with gzip.open(path, "rt") as f:
                _LOOKUP = json.load(f)
        else:
            with open(os.path.join(_HERE, "sponsorship_lookup.json")) as f:
                _LOOKUP = json.load(f)
        _KEYS = sorted(_LOOKUP)
    return _LOOKUP, _KEYS

def _norm(name):
    s = re.sub(r"[^A-Z0-9 ]", " ", str(name or "").upper())
    s = re.sub(r"\s+", " ", s).strip()
    return " ".join(t for t in s.split() if t.lower() not in _SUFFIX) or s

def _match_keys(company):
    L, keys = _load()
    q = _norm(company)
    q = _ALIAS.get(q.lower().replace(" ", ""), q)
    if not q:
        return []
    i = bisect.bisect_left(keys, q)
    out = []
    while i < len(keys) and keys[i].startswith(q):
        if keys[i] == q or keys[i].startswith(q + " "):
            out.append(keys[i])
        i += 1
    return out

def _tier(total):
    if total >= 50: return "Strong"
    if total >= 10: return "Moderate"
    if total >= 2:  return "Light"
    if total >= 1:  return "Minimal"
    return "None"

def get_sponsorship(company, market="US"):
    """Return (summary_string, facts_dict)."""
    if market == "India":
        return ("N/A - India (citizen)", {"tier": "N/A"})
    if market == "Canada":
        return ("Express Entry - no lottery", {"tier": "N/A"})

    L, _ = _load()
    ms = _match_keys(company)
    if not ms:
        return ("None - no FY25 H-1B filings",
                {"tier": "None", "total": 0, "role": 0, "ut": 0})

    total = sum(L[m]["total"] for m in ms)
    role  = sum(L[m]["role"] for m in ms)
    ut    = sum(L[m]["ut"] for m in ms)
    qs    = sorted({q for m in ms for q in L[m]["quarters"]})
    latest = max(L[m]["latest"] for m in ms)
    tier  = _tier(total)

    bits = [f"{tier} - {total} LCAs (FY25)"]
    if role: bits.append(f"{role} PM/analyst")
    if ut:   bits.append(f"{ut} in UT")
    summary = " | ".join(bits)
    return (summary, {"tier": tier, "total": total, "role": role, "ut": ut,
                      "quarters": qs, "latest": latest,
                      "entities": [L[m]["name"] for m in ms[:5]]})

if __name__ == "__main__":
    for c, mk in [("Adobe","US"),("Goldman Sachs","US"),("Podium","US"),
                  ("Deloitte","US"),("Razorpay","India")]:
        s, f = get_sponsorship(c, mk)
        print(f"{c:<16} -> {s}")
