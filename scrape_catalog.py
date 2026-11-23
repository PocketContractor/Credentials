import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "catalog.json"
INDEX_FILE = ROOT / "index.html"


def bootstrap_catalog() -> list[dict]:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    if INDEX_FILE.exists():
        text = INDEX_FILE.read_text(encoding="utf-8")
        match = re.search(r"const EMBEDDED_CATALOG = (\[.*?\]);", text, re.S)
        if match:
            return json.loads(match.group(1))
    return []


def next_uid(existing: list[dict], sector: str) -> str:
    prefix_map = {
        "TRADE": "TRD",
        "INDUSTRY": "IND",
        "PUBLIC": "PUB",
        "ACADEMIC": "ACD",
        "FORCES": "FRC",
    }
    prefix = prefix_map.get(sector, "GEN")
    pattern = re.compile(rf"^CRED-{prefix}-(\d+)$")
    max_num = 0
    for item in existing:
        m = pattern.match(str(item.get("uid", "")))
        if m:
            max_num = max(max_num, int(m.group(1)))
    return f"CRED-{prefix}-{max_num + 1:03d}"


def fetch_red_seal_candidates() -> list[dict]:
    url = "https://www.red-seal.ca/eng/trades/tr.1d.2s_l.3st.shtml"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PocketCreditBot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    candidates = []
    for m in re.finditer(r"<a[^>]*>([^<]{4,80})</a>", html):
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        if any(k in title.lower() for k in ("electrician", "plumber", "welder", "carpenter", "millwright", "machinist")):
            candidates.append({
                "sector": "TRADE",
                "category": "Red Seal Candidate",
                "code": "RS",
                "name": title,
                "authority": "Red Seal Program",
                "otj_hours": 0,
                "blocks": 0,
                "status": "Not Started",
                "notes": "Discovered via weekly Red Seal check.",
            })
    return candidates


def main() -> None:
    existing = bootstrap_catalog()
    known_names = {str(x.get("name", "")).strip().lower() for x in existing}
    added = 0

    for cand in fetch_red_seal_candidates():
        norm_name = cand["name"].strip().lower()
        if norm_name and norm_name not in known_names:
            cand["uid"] = next_uid(existing, cand["sector"])
            existing.append(cand)
            known_names.add(norm_name)
            added += 1

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    print(f"Catalog total: {len(existing)} (added: {added})")


if __name__ == "__main__":
    main()
