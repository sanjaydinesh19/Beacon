from fastapi import APIRouter, HTTPException
from github import Github, GithubException
from datetime import datetime, timezone
from notion_journal import config

router = APIRouter()


def _time_ago(dt: datetime) -> str:
    diff = int((datetime.now(timezone.utc) - dt).total_seconds())
    if diff < 60:
        return "just now"
    if diff < 3600:
        return f"{diff // 60}m ago"
    if diff < 86400:
        return f"{diff // 3600}h ago"
    return f"{diff // 86400}d ago"


@router.get("/activity")
def get_activity():
    try:
        g = Github(config.require("GITHUB_TOKEN"))
        user = g.get_user()
        username = user.login

        items = []
        for event in user.get_events():
            if len(items) >= 40:
                break

            repo_full = event.repo.name
            repo_name = repo_full.split("/", 1)[-1]
            t = _time_ago(event.created_at)

            if event.type == "PushEvent":
                for commit in event.payload.get("commits", [])[:2]:
                    msg = commit.get("message", "").split("\n")[0].strip()
                    if not msg:
                        continue
                    items.append({
                        "type": "commit",
                        "repo": repo_name,
                        "repoFull": repo_full,
                        "title": msg,
                        "url": f"https://github.com/{repo_full}/commit/{commit.get('sha', '')}",
                        "time": t,
                        "meta": commit.get("sha", "")[:7],
                        "number": None,
                    })

            elif event.type == "PullRequestEvent":
                action = event.payload.get("action", "")
                if action not in ("opened", "closed"):
                    continue
                pr = event.payload.get("pull_request", {})
                merged = pr.get("merged", False)
                state = "merged" if (action == "closed" and merged) else action
                items.append({
                    "type": "pr",
                    "repo": repo_name,
                    "repoFull": repo_full,
                    "title": pr.get("title", ""),
                    "url": pr.get("html_url", ""),
                    "time": t,
                    "meta": state,
                    "number": pr.get("number"),
                })

        return {"username": username, "items": items[:30]}

    except GithubException as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
