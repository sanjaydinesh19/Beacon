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

# Tracks the highest submission timestamp we've already committed to the log.
# Resets to 0 on backend restart (intentional — we re-generate on startup if
# there are any solves today, which keeps the log correct after crashes).
_last_processed_ts: int = 0


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
    """Commit tracker.json to the backup repo. Runs daily at midnight IST."""
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


def _deduplicate_subs(subs: list[dict]) -> list[dict]:
    """One entry per problem per day — keep the submission with the latest timestamp."""
    best: dict[str, dict] = {}
    for s in subs:
        slug = s["titleSlug"]
        if slug not in best or int(s["timestamp"]) > int(best[slug]["timestamp"]):
            best[slug] = s
    return sorted(best.values(), key=lambda s: int(s["timestamp"]))


async def _fetch_problem_detail(slug: str, client: httpx.AsyncClient) -> dict:
    query = """
    query questionData($titleSlug: String!) {
      question(titleSlug: $titleSlug) {
        questionFrontendId
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
            "number": q.get("questionFrontendId", "?"),
            "difficulty": q.get("difficulty", "Unknown"),
            "topics": [t["name"] for t in (q.get("topicTags") or [])],
        }
    except Exception:
        return {"number": "?", "difficulty": "Unknown", "topics": []}


async def generate_daily_lc():
    """Fetch today's LC solves (deduplicated), commit a dated markdown to the backup repo."""
    global _last_processed_ts
    today = date.today()
    today_ist = datetime.now(IST)

    try:
        raw_subs = await _fetch_lc_submissions_today()
        subs = _deduplicate_subs(raw_subs)

        if not subs:
            log.info("LC daily: no problems solved today (%s), skipping commit", today)
            return

        async with httpx.AsyncClient() as client:
            details: dict[str, dict] = {}
            for s in subs[:20]:
                details[s["titleSlug"]] = await _fetch_problem_detail(s["titleSlug"], client)

        diff_icon = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}

        rows = []
        for s in subs:
            d = details.get(s["titleSlug"], {})
            difficulty = d.get("difficulty", "Unknown")
            topics = d.get("topics", [])
            icon = diff_icon.get(difficulty, "⚪")
            num = d.get("number", "?")
            solved_at = datetime.fromtimestamp(int(s["timestamp"]), tz=IST).strftime("%H:%M IST")
            rows.append((num, s["title"], s["titleSlug"], icon, difficulty, topics, solved_at))

        table_lines = [
            "| # | Problem | Difficulty | Topics | Solved At |",
            "|---|---------|-----------|--------|-----------|",
        ]
        for num, title, slug, icon, diff, topics, solved_at in rows:
            topics_str = ", ".join(topics) if topics else "—"
            link = f"[{num}. {title}](https://leetcode.com/problems/{slug}/)"
            table_lines.append(f"| {num} | {link} | {icon} {diff} | {topics_str} | {solved_at} |")

        easy = sum(1 for *_, d, _, _ in rows if d == "Easy")
        medium = sum(1 for *_, d, _, _ in rows if d == "Medium")
        hard = sum(1 for *_, d, _, _ in rows if d == "Hard")

        lines = [
            f"# LeetCode Daily Log — {today.isoformat()}",
            "",
            f"**{len(rows)} solved** · 🟢 {easy} Easy · 🟡 {medium} Medium · 🔴 {hard} Hard",
            "",
            *table_lines,
            "",
            "---",
            "",
        ]

        for i, (num, title, slug, icon, diff, topics, solved_at) in enumerate(rows, 1):
            topics_str = ", ".join(topics) if topics else "—"
            lines += [
                f"## {i}. #{num} {title}  {icon} {diff}",
                f"- **Topics**: {topics_str}",
                f"- **Solved at**: {solved_at}",
                f"- **Link**: https://leetcode.com/problems/{slug}/",
                "",
            ]

        lines.append(f"*Generated by Beacon · {today_ist.strftime('%Y-%m-%d %H:%M IST')}*")

        content = "\n".join(lines)
        g = _get_github()
        _, repo = _get_repo(g)
        path = f"lc-daily/{today.isoformat()}.md"
        _commit_file(repo, path, content, f"lc: {today.isoformat()} ({len(rows)} solved)")
        log.info("LC daily committed: %s (%d problems)", today, len(rows))

        # Advance the watermark so the poll job knows we're up to date
        if subs:
            _last_processed_ts = max(int(s["timestamp"]) for s in subs)

    except Exception as e:
        log.error("LC daily failed: %s", e)


async def poll_lc():
    """Check for new accepted submissions every 5 min; regenerate the log if found."""
    global _last_processed_ts
    try:
        subs = await _fetch_lc_submissions_today()
        if not subs:
            return
        latest_ts = max(int(s["timestamp"]) for s in subs)
        if latest_ts > _last_processed_ts:
            log.info("LC poll: new submission detected (ts=%d), regenerating log", latest_ts)
            await generate_daily_lc()
    except Exception as e:
        log.error("LC poll failed: %s", e)


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

    # Tracker backup — daily at midnight IST
    _scheduler.add_job(
        auto_backup,
        CronTrigger(hour=0, minute=0, timezone="Asia/Kolkata"),
        id="backup_tracker",
        replace_existing=True,
    )

    # LC poll — every 5 minutes, triggers log regeneration on new solve
    _scheduler.add_job(poll_lc, IntervalTrigger(minutes=5), id="lc_poll", replace_existing=True)

    # LC safety regeneration — every 6 hours regardless of poll state
    _scheduler.add_job(generate_daily_lc, IntervalTrigger(hours=6), id="lc_daily", replace_existing=True)

    _scheduler.start()
    log.info("Scheduler started — tracker backup at 00:00 IST, LC poll every 5min, LC regen every 6h")


def shutdown_scheduler():
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
