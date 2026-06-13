import json
import time
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException
from github import Github, GithubException
import httpx
from notion_journal import config

router = APIRouter()

# Simple in-memory cache: key → {ts, data}
_cache: dict = {}
CONTRIB_TTL = 1800  # 30 min


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

@router.get("/activity")
def get_activity():
    try:
        g = Github(config.require("GITHUB_TOKEN"))
        auth_user = g.get_user()
        username = auth_user.login
        # AuthenticatedUser.get_events() hits /events (network feed, not yours).
        # NamedUser.get_events() hits /users/{login}/events — your own events.
        named_user = g.get_user(username)

        items = []
        for event in named_user.get_events():
            if len(items) >= 40:
                break

            repo_full = event.repo.name
            repo_name = repo_full.split("/", 1)[-1]
            t = _time_ago(event.created_at)

            if event.type == "PushEvent":
                for commit in event.payload.get("commits", [])[:2]:
                    msg = commit.get("message", "").split("\n")[0].strip()
                    sha = commit.get("sha", "")
                    if not msg or not sha:
                        continue
                    items.append({
                        "type": "commit",
                        "repo": repo_name,
                        "repoFull": repo_full,
                        "title": msg,
                        "url": f"https://github.com/{repo_full}/commit/{sha}",
                        "time": t,
                        "meta": sha[:7],
                        "number": None,
                    })

            elif event.type == "PullRequestEvent":
                action = event.payload.get("action", "")
                if action not in ("opened", "closed"):
                    continue
                pr = event.payload.get("pull_request", {})
                html_url = pr.get("html_url", "")
                if not html_url:
                    continue
                merged = pr.get("merged", False)
                state = "merged" if (action == "closed" and merged) else action
                items.append({
                    "type": "pr",
                    "repo": repo_name,
                    "repoFull": repo_full,
                    "title": pr.get("title", ""),
                    "url": html_url,
                    "time": t,
                    "meta": state,
                    "number": pr.get("number"),
                })

        return {"username": username, "items": items[:30]}

    except GithubException as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GitHub Contributions ────────────────────────────────────────────────────

_LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

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


@router.get("/contributions")
def get_contributions():
    token = config.require("GITHUB_TOKEN")

    def fetch():
        g = Github(token)
        username = g.get_user().login

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
    # Roll back to Sunday
    start -= timedelta(days=(start.weekday() + 1) % 7)

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
        total = sum(raw.values())
        return {
            "username": LEETCODE_USERNAME,
            "total": total,
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
