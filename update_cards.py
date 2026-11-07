"""Refreshes data.json from LeetCode / CodeChef, then redraws the two SVG cards.
If a site can't be reached or its page layout changed, the old values are kept."""
import json
import re
import sys
from pathlib import Path

import requests

LEETCODE_USER = "Shruticodes-afk"
CODECHEF_USER = "paavbhaaji"
DATA = Path("data.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}


def fetch_leetcode(d):
    query = """query($u:String!){userContestRanking(username:$u){
        attendedContestsCount rating globalRanking totalParticipants topPercentage}}"""
    r = requests.post(
        "https://leetcode.com/graphql",
        json={"query": query, "variables": {"u": LEETCODE_USER}},
        headers={**HEADERS, "Content-Type": "application/json", "Referer": "https://leetcode.com"},
        timeout=30,
    )
    r.raise_for_status()
    c = r.json()["data"]["userContestRanking"]
    if not c:
        print("LeetCode: no contest data")
        return
    d["leetcode"].update(
        rating=round(c["rating"]),
        global_rank=c["globalRanking"],
        total=c["totalParticipants"],
        attended=c["attendedContestsCount"],
        top=round(c["topPercentage"], 2),
    )
    print("LeetCode updated:", d["leetcode"])


def grab(pattern, html, group=1, flags=0):
    m = re.search(pattern, html, flags)
    return int(m.group(group)) if m else None


def fetch_codechef(d):
    r = requests.get(f"https://www.codechef.com/users/{CODECHEF_USER}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    html = r.text
    cc = d["codechef"]

    found = {
        "solved": grab(r"Total Problems Solved:\s*(\d+)", html),
        "contests": grab(r"No\. of Contests Participated:\s*(?:<[^>]+>\s*)*(\d+)", html),
        "dsa_contests": grab(r"No\. of DSA Contests Participated:\s*(?:<[^>]+>\s*)*(\d+)", html),
    }
    ratings = re.findall(r'class="rating-number"[^>]*>\s*(\d+)', html)
    if ratings:
        found["rating"] = int(ratings[0])
        if len(ratings) > 1:
            found["dsa_rating"] = int(ratings[1])
    globals_ = re.findall(r"<strong>(\d+)</strong>\s*(?:</a>)?\s*Global Rank", html)
    countries = re.findall(r"<strong>(\d+)</strong>\s*(?:</a>)?\s*Country Rank", html)
    if globals_:
        found["global_rank"] = int(globals_[0])
    if len(globals_) > 1:
        found["dsa_global_rank"] = int(globals_[1])
    if countries:
        found["country_rank"] = int(countries[0])
    if len(countries) > 1:
        found["dsa_country_rank"] = int(countries[1])

    for k, v in found.items():
        if v is not None:
            cc[k] = v
    cc["highest"] = max(cc["highest"], cc["rating"])
    cc["dsa_highest"] = max(cc["dsa_highest"], cc["dsa_rating"])
    print("CodeChef parsed:", {k: v for k, v in found.items() if v is not None})


HEIGHTS = [6, 6, 6, 16, 34, 88, 74, 52, 36, 26, 18, 13, 10, 8, 7, 6, 6, 6, 6, 6, 6, 6, 6, 6]


def leetcode_svg(lc):
    idx = max(0, min(len(HEIGHTS) - 1, round((lc["rating"] - 900) / 150)))
    bars = ""
    for i, h in enumerate(HEIGHTS):
        color = "#ffa116" if i == idx else "#444444"
        bars += f'  <rect x="{366 + i * 16}" y="{170 - h}" width="12" height="{h}" rx="1.5" fill="{color}"/>\n'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="780" height="200" viewBox="0 0 780 200" font-family="Segoe UI, Arial, sans-serif">
  <rect width="780" height="200" rx="10" fill="#282828"/>
  <text x="24" y="40" fill="#bdbdbd" font-size="13" font-weight="600">Contest Rating</text>
  <text x="24" y="82" fill="#ffffff" font-size="36">{lc["rating"]:,}</text>
  <text x="24" y="122" fill="#bdbdbd" font-size="13">Global Ranking</text>
  <text x="24" y="144" fill="#ffffff" font-size="15" font-weight="700">{lc["global_rank"]:,}<tspan fill="#8a8a8a" font-weight="400">/{lc["total"]:,}</tspan></text>
  <text x="220" y="122" fill="#bdbdbd" font-size="13">Attended</text>
  <text x="220" y="144" fill="#ffffff" font-size="15" font-weight="700">{lc["attended"]}</text>
  <line x1="340" y1="20" x2="340" y2="180" stroke="#3a3a3a" stroke-width="1"/>
  <text x="366" y="40" fill="#bdbdbd" font-size="13">Top</text>
  <text x="366" y="80" fill="#ffffff" font-size="34">{lc["top"]}%</text>
{bars}</svg>
'''


def codechef_svg(c):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="320" viewBox="0 0 500 320" font-family="'Fira Code', Consolas, 'Courier New', monospace">
  <rect x="0.5" y="0.5" width="499" height="319" rx="6" fill="#0e0e0e" stroke="#333333"/>
  <text x="24" y="40" fill="#ffffff" font-size="22" font-weight="700">{CODECHEF_USER}</text>
  <text x="476" y="40" fill="#b9a089" font-size="14" font-weight="700" text-anchor="end">{c["stars"]}★  Div {c["div"]}</text>
  <text x="24" y="62" fill="#8a8a8a" font-size="12">CodeChef</text>
  <line x1="24" y1="76" x2="476" y2="76" stroke="#2a2a2a"/>

  <text x="24" y="104" fill="#9a9a9a" font-size="12">CodeChef Rating</text>
  <text x="24" y="148" fill="#ffffff" font-size="42">{c["rating"]}</text>
  <text x="24" y="170" fill="#8a8a8a" font-size="11">Highest {c["highest"]}</text>
  <text x="24" y="194" fill="#d0d0d0" font-size="12">Global   #{c["global_rank"]:,}</text>
  <text x="24" y="214" fill="#d0d0d0" font-size="12">Country  #{c["country_rank"]:,}</text>

  <line x1="250" y1="92" x2="250" y2="222" stroke="#2a2a2a"/>

  <text x="274" y="104" fill="#9a9a9a" font-size="12">DSA Rating</text>
  <text x="274" y="148" fill="#ffa116" font-size="42">{c["dsa_rating"]}</text>
  <text x="274" y="170" fill="#8a8a8a" font-size="11">Highest {c["dsa_highest"]}</text>
  <text x="274" y="194" fill="#d0d0d0" font-size="12">Global   #{c["dsa_global_rank"]:,}</text>
  <text x="274" y="214" fill="#d0d0d0" font-size="12">Country  #{c["dsa_country_rank"]:,}</text>

  <line x1="24" y1="240" x2="476" y2="240" stroke="#2a2a2a"/>

  <text x="24" y="268" fill="#9a9a9a" font-size="12">Problems Solved</text>
  <text x="24" y="298" fill="#ffffff" font-size="24">{c["solved"]}</text>
  <text x="200" y="268" fill="#9a9a9a" font-size="12">Contests</text>
  <text x="200" y="298" fill="#ffffff" font-size="24">{c["contests"]}</text>
  <text x="330" y="268" fill="#9a9a9a" font-size="12">DSA Contests</text>
  <text x="330" y="298" fill="#ffffff" font-size="24">{c["dsa_contests"]}</text>
</svg>
'''


def main():
    data = json.loads(DATA.read_text())
    for name, fn in (("LeetCode", fetch_leetcode), ("CodeChef", fetch_codechef)):
        try:
            fn(data)
        except Exception as e:  # keep old values on any failure
            print(f"{name}: skipped ({e})", file=sys.stderr)
    DATA.write_text(json.dumps(data, indent=2) + "\n")
    Path("leetcode-contest.svg").write_text(leetcode_svg(data["leetcode"]))
    Path("codechef-card.svg").write_text(codechef_svg(data["codechef"]))
    print("Cards written.")


if __name__ == "__main__":
    main()
