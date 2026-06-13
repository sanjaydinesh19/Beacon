import json
import time
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
import httpx
from notion_journal import config

router = APIRouter()

_cache: dict = {}
ACTIVITY_TTL = 300   # 5 min
CONTRIB_TTL = 1800   # 30 min


def _cached(key: str, ttl: int, fn):
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < ttl:
        return _cache[key]["data"]
    data = fn()
    _cache[key] = {"ts": now, "data": data}
    return data


def _time_ago(dt: datetime) -> str:
    diff = int((datetime.now(timezone.utc) - dt).total_seconds())
    if diff < 60:
        return "just now"
    if diff < 3600:
        return f"{diff // 60}m ago"
    if diff < 86400:
        return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


# ── Activity ────────────────────────────────────────────────────────────────
# NOTE: The GitHub Events API strips `commits` from PushEvent payloads in
# recent API versions. We fetch commits directly per-repo instead.

@router.get("/activity")
def get_activity():
    token = config.require("GITHUB_TOKEN")

    def fetch():
        hdrs = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        me = httpx.get("https://api.github.com/user", headers=hdrs, timeout=10).json()
        username = me["login"]

        raw: list[tuple[datetime, dict]] = []

        # ── Commits: most recently pushed repos ───────────────────────────
        repos_resp = httpx.get(
            "https://api.github.com/user/repos",
            headers=hdrs,
            params={"sort": "pushed", "per_page": 8, "affiliation": "owner"},
            timeout=10,
        )
        repos = repos_resp.json() if repos_resp.status_code == 200 else []

        for repo in repos[:8]:
            repo_name = repo["name"]
            repo_full = repo["full_name"]
            c_resp = httpx.get(
                f"https://api.github.com/repos/{repo_full}/commits",
                headers=hdrs,
                params={"author": username, "per_page": 3},
                timeout=10,
            )
            if c_resp.status_code != 200:
                continue
            for c in c_resp.json()[:3]:
                msg = c["commit"]["message"].split("\n")[0].strip()
                if not msg:
                    continue
                dt_str = c["commit"]["committer"]["date"]
                dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                raw.append((dt, {
                    "type": "commit",
                    "repo": repo_name,
                    "repoFull": repo_full,
                    "title": msg,
                    "url": c["html_url"],
                    "meta": c["sha"][:7],
                    "number": None,
                }))

        # ── PRs ───────────────────────────────────────────────────────────
        pr_resp = httpx.get(
            "https://api.github.com/search/issues",
            headers=hdrs,
            params={
                "q": f"author:{username} type:pr",
                "sort": "created",
                "order": "desc",
                "per_page": 15,
            },
            timeout=10,
        )
        if pr_resp.status_code == 200:
            for pr in pr_resp.json().get("items", []):
                repo_full = pr["repository_url"].split("/repos/")[-1]
                repo_name = repo_full.split("/")[-1]
                state = pr["state"]
                if state == "closed" and pr.get("pull_request", {}).get("merged_at"):
                    state = "merged"
                dt = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                raw.append((dt, {
                    "type": "pr",
                    "repo": repo_name,
                    "repoFull": repo_full,
                    "title": pr["title"],
                    "url": pr["html_url"],
                    "meta": state,
                    "number": pr["number"],
                }))

        # Sort by datetime descending, attach relative timestamps
        raw.sort(key=lambda x: x[0], reverse=True)
        items = []
        for dt, d in raw[:30]:
            d["time"] = _time_ago(dt)
            items.append(d)

        return {"username": username, "items": items}

    try:
        return _cached("gh_activity", ACTIVITY_TTL, fetch)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GitHub Contributions ────────────────────────────────────────────────────

_GH_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

_LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


@router.get("/contributions")
def get_contributions():
    token = config.require("GITHUB_TOKEN")

    def fetch():
        me = httpx.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        ).json()
        username = me["login"]

        resp = httpx.post(
            "https://api.github.com/graphql",
            json={"query": _GH_QUERY, "variables": {"login": username}},
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()

        if "errors" in body:
            raise HTTPException(status_code=502, detail=body["errors"][0]["message"])

        cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        weeks = [
            [
                {
                    "date": d["date"],
                    "count": d["contributionCount"],
                    "level": _LEVEL_MAP.get(d["contributionLevel"], 0),
                }
                for d in week["contributionDays"]
            ]
            for week in cal["weeks"]
        ]
        return {"total": cal["totalContributions"], "weeks": weeks, "username": username}

    try:
        return _cached("gh_contributions", CONTRIB_TTL, fetch)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── LeetCode Contributions ──────────────────────────────────────────────────

_LC_QUERY = """
query userCalendar($username: String!) {
  matchedUser(username: $username) {
    userCalendar {
      submissionCalendar
      totalActiveDays
      streak
    }
  }
}
"""

LEETCODE_USERNAME = "sanjaydinesh"


def _build_lc_grid(submission_calendar: dict) -> list:
    today = date.today()
    start = today - timedelta(weeks=52)
    start -= timedelta(days=(start.weekday() + 1) % 7)  # roll back to Sunday

    weeks = []
    current = start
    while current <= today:
        week = []
        for offset in range(7):
            d = current + timedelta(days=offset)
            ts = str(int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp()))
            count = submission_calendar.get(ts, 0)
            level = 0 if count == 0 else (1 if count < 3 else (2 if count < 6 else (3 if count < 10 else 4)))
            week.append({"date": d.isoformat(), "count": count, "level": level})
        weeks.append(week)
        current += timedelta(weeks=1)
    return weeks


@router.get("/leetcode")
def get_leetcode():
    def fetch():
        resp = httpx.post(
            "https://leetcode.com/graphql/",
            json={"query": _LC_QUERY, "variables": {"username": LEETCODE_USERNAME}},
            headers={
                "Content-Type": "application/json",
                "Referer": "https://leetcode.com",
                "User-Agent": "Mozilla/5.0",
            },
            timeout=15,
        )
        resp.raise_for_status()
        body = resp.json()

        matched = body.get("data", {}).get("matchedUser")
        if not matched:
            raise HTTPException(status_code=404, detail="LeetCode user not found")

        cal = matched["userCalendar"]
        raw = json.loads(cal["submissionCalendar"])
        weeks = _build_lc_grid(raw)
        return {
            "username": LEETCODE_USERNAME,
            "total": sum(raw.values()),
            "totalActiveDays": cal["totalActiveDays"],
            "streak": cal["streak"],
            "weeks": weeks,
        }

    try:
        return _cached("lc_contributions", CONTRIB_TTL, fetch)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
