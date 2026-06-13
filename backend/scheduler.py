import json
import logging
from datetime import datetime, date, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from github import Github, GithubException

from notion_journal import config

log = logging.getLogger("beacon.scheduler")
IST = ZoneInfo("Asia/Kolkata")

DATA_DIR = Path(__file__).parent / "data"
TRACKER_FILE = DATA_DIR / "tracker.json"
BACKUP_REPO = "beacon-placements"
LC_USERNAME = "sanjaydinesh"

_scheduler: AsyncIOScheduler | None = None


def _get_github():
    token = config.require("GITHUB_TOKEN")
    return Github(token)


def _get_repo(g: Github):
    user = g.get_user()
    try:
        return user, user.get_repo(BACKUP_REPO)
    except GithubException:
        repo = user.create_repo(
            BACKUP_REPO,
            private=True,
            description="Beacon placement tracker & LeetCode daily log",
            auto_init=True,
        )
        return user, repo


def _commit_file(repo, path: str, content: str, message: str):
    try:
        existing = repo.get_contents(path)
        repo.update_file(path, message, content, existing.sha)
    except GithubException:
        repo.create_file(path, message, content)


async def auto_backup():
    """Commit tracker.json to the backup repo. Runs every 6 hours."""
    try:
        g = _get_github()
        _, repo = _get_repo(g)

        content = TRACKER_FILE.read_text()
        timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
        _commit_file(repo, "tracker.json", content, f"tracker: {timestamp}")

        tracker = json.loads(content)
        tracker["lastBackup"] = datetime.now(timezone.utc).isoformat()
        TRACKER_FILE.write_text(json.dumps(tracker, indent=2))
        log.info("Auto-backup complete: %s", timestamp)
    except Exception as e:
        log.error("Auto-backup failed: %s", e)


async def _fetch_lc_submissions_today() -> list[dict]:
    today_ist = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_ts = int(today_ist.timestamp())

    query = """
    query recentAcSubmissions($username: String!, $limit: Int!) {
      recentAcSubmissionList(username: $username, limit: $limit) {
        id title titleSlug timestamp
      }
    }
    """
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://leetcode.com/graphql",
            json={"query": query, "variables": {"username": LC_USERNAME, "limit": 50}},
            headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
            timeout=15,
        )
        data = r.json()

    all_subs = data.get("data", {}).get("recentAcSubmissionList") or []
    return [s for s in all_subs if int(s["timestamp"]) >= cutoff_ts]


async def _fetch_problem_detail(slug: str, client: httpx.AsyncClient) -> dict:
    query = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        difficulty
        topicTags { name }
      }
    }
    """
    try:
        r = await client.post(
            "https://leetcode.com/graphql",
            json={"query": query, "variables": {"titleSlug": slug}},
            headers={"Content-Type": "application/json", "Referer": "https://leetcode.com"},
            timeout=10,
        )
        q = r.json().get("data", {}).get("question") or {}
        return {
            "difficulty": q.get("difficulty", "Unknown"),
            "topics": [t["name"] for t in (q.get("topicTags") or [])],
        }
    except Exception:
        return {"difficulty": "Unknown", "topics": []}


async def generate_daily_lc():
    """Fetch today's LeetCode activity and commit a dated markdown to the backup repo."""
    today = date.today()
    today_ist = datetime.now(IST)

    try:
        subs = await _fetch_lc_submissions_today()

        if not subs:
            log.info("LC daily: no problems solved today (%s), skipping commit", today)
            return

        async with httpx.AsyncClient() as client:
            details: dict[str, dict] = {}
            for s in subs[:20]:
                details[s["titleSlug"]] = await _fetch_problem_detail(s["titleSlug"], client)

        lines = [
            f"# LeetCode Daily Log — {today.isoformat()}",
            "",
            f"**Problems Solved**: {len(subs)}",
            "",
            "---",
            "",
        ]

        diff_icon = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}

        for i, s in enumerate(subs, 1):
            solved_at = datetime.fromtimestamp(int(s["timestamp"]), tz=IST).strftime("%H:%M IST")
            d = details.get(s["titleSlug"], {})
            difficulty = d.get("difficulty", "Unknown")
            topics = d.get("topics", [])
            icon = diff_icon.get(difficulty, "⚪")

            lines += [
                f"## {i}. {s['title']} {icon} {difficulty}",
                f"- **Solved at**: {solved_at}",
            ]
            if topics:
                lines.append(f"- **Topics**: {', '.join(topics)}")
            lines += [
                f"- **Link**: https://leetcode.com/problems/{s['titleSlug']}/",
                "",
            ]

        lines.append(f"*Generated by Beacon · {today_ist.strftime('%Y-%m-%d %H:%M IST')}*")

        content = "\n".join(lines)
        g = _get_github()
        _, repo = _get_repo(g)
        path = f"lc-daily/{today.isoformat()}.md"
        _commit_file(repo, path, content, f"lc: {today.isoformat()} ({len(subs)} solved)")
        log.info("LC daily committed: %s (%d problems)", today, len(subs))
    except Exception as e:
        log.error("LC daily failed: %s", e)


def ensure_backup_repo():
    """Create the backup repo on startup if it doesn't exist."""
    try:
        g = _get_github()
        _, repo = _get_repo(g)
        log.info("Backup repo ready: github.com/%s/%s", repo.owner.login, BACKUP_REPO)
    except Exception as e:
        log.warning("Could not init backup repo: %s", e)


def init_scheduler():
    global _scheduler
    _scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(auto_backup, IntervalTrigger(hours=6), id="backup_tracker", replace_existing=True)
    _scheduler.add_job(
        generate_daily_lc,
        CronTrigger(hour=23, minute=0, timezone="Asia/Kolkata"),
        id="lc_daily",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("Scheduler started — backup every 6h, LC summary at 23:00 IST")


def shutdown_scheduler():
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
