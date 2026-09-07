from datetime import datetime, timezone, timedelta
import json
import os
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN")
LOGIN = os.environ.get("GH_LOGIN", "mokshithk")


def run_query(query, variables):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "profile-updater",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    now = datetime.now(timezone.utc)
    date_to = now.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    date_from = (now - timedelta(days=364)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
              }
            }
          }
        }
      }
    }
    """

    res = run_query(query, {"login": LOGIN, "from": date_from, "to": date_to})
    calendar = res["data"]["user"]["contributionsCollection"]["contributionCalendar"]

    days = [d for week in calendar["weeks"] for d in week["contributionDays"]]

    # Calculate streak
    longest, current, temp = 0, 0, 0
    for d in days:
        if d["contributionCount"] > 0:
            temp += 1
            if temp > longest:
                longest = temp
        else:
            temp = 0
    current = temp

    # Generate year.svg
    ramp = " :+#@"
    year_str = "".join(ramp[min(len(ramp) - 1, d["contributionCount"])] for d in days)
    svg_year = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 30" width="700" height="30">
  <style>
    text {{ font-family: monospace; font-size: 11px; fill: #24292f; letter-spacing: 2px; }}
    @media (prefers-color-scheme: dark) {{ text {{ fill: #8b949e; }} }}
  </style>
  <text x="0" y="18">{year_str}</text>
</svg>"""
    with open("year.svg", "w", encoding="utf-8") as f:
        f.write(svg_year)

    # Generate stats.svg
    total = calendar["totalContributions"]
    svg_stats = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 350 30" width="350" height="30">
  <style>
    text {{ font-family: monospace; font-size: 13px; fill: #24292f; }}
    .dim {{ fill: #57606a; }}
    @media (prefers-color-scheme: dark) {{ text {{ fill: #f0f6fc; }} .dim {{ fill: #8b949e; }} }}
  </style>
  <text x="0" y="20">contributions: <tspan class="dim">{total} in past year</tspan></text>
</svg>"""
    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(svg_stats)

    # Generate streak.svg
    svg_streak = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 350 30" width="350" height="30">
  <style>
    text {{ font-family: monospace; font-size: 13px; fill: #24292f; }}
    .dim {{ fill: #57606a; }}
    @media (prefers-color-scheme: dark) {{ text {{ fill: #f0f6fc; }} .dim {{ fill: #8b949e; }} }}
  </style>
  <text x="0" y="20">streak: <tspan class="dim">{current} days (longest: {longest})</tspan></text>
</svg>"""
    with open("streak.svg", "w", encoding="utf-8") as f:
        f.write(svg_streak)


if __name__ == "__main__":
    main()