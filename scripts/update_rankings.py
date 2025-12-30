import requests
import json
from datetime import datetime
import re

# --- CONFIG ---
GITHUB_API_BASE = "https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings/contents/live"
RAW_BASE = "https://raw.githubusercontent.com/ValveSoftware/counter-strike_regional_standings/main/live/"
REGIONS = ["global", "eu", "na", "asia"]
REGION_MAP = {
    "global": "global",
    "eu": "europe",
    "na": "americas",
    "asia": "asia"
}
OUTPUT_FILE = "../valve_rankings.json"

def parse_md(content):
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("| Rank") or line.startswith("|---"):
            continue
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 3:
            try:
                rank = int(parts[0])
                points = int(parts[1])
                tag = parts[2]
                entries.append({"rank": rank, "points": points, "tag": tag})
            except ValueError:
                continue
    return entries

def get_latest_year_folder():
    """Return the latest year folder that actually exists in the repo."""
    resp = requests.get(GITHUB_API_BASE)
    resp.raise_for_status()
    folders = [item['name'] for item in resp.json() if item['type'] == 'dir']
    if not folders:
        raise RuntimeError("No year folders found in the repo!")
    return str(max(int(f) for f in folders))

def get_latest_file_for_region(year, region_name):
    url = f"https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings/contents/live/{year}"
    resp = requests.get(url)
    resp.raise_for_status()
    files = [item['name'] for item in resp.json() if item['type'] == 'file']
    # region_name is already mapped to the Valve naming convention
    pattern = re.compile(rf"standings_{region_name}_{year}_(\d{{2}})_(\d{{2}})\.md")
    candidates = []
    for f in files:
        m = pattern.match(f)
        if m:
            month, day = int(m.group(1)), int(m.group(2))
            candidates.append((month, day, f))
    if not candidates:
        return None
    latest = max(candidates)
    return f"https://raw.githubusercontent.com/ValveSoftware/counter-strike_regional_standings/main/live/{year}/{latest[2]}"

def fetch_region(region, year):
    region_name = REGION_MAP[region]
    url = get_latest_file_for_region(year, region_name)
    if not url:
        print(f"No file found for {region} ({region_name}) in {year}")
        return []
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Failed to fetch {region}: {resp.status_code}")
        return []
    return parse_md(resp.text)

def main():
    rankings = {"updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    latest_year = get_latest_year_folder()
    for region in REGIONS:
        rankings[region] = fetch_region(region, latest_year)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(rankings, f, indent=2)
    print(f"Written {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
