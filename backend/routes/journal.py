import sys
import tempfile
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

# Load env: Beacon's own .env first, then fall back to Notion Journal's .env
_BACKEND_ROOT = Path(__file__).parent.parent
_JOURNAL_ROOT = _BACKEND_ROOT.parent.parent / "Notion Journal"

load_dotenv(_BACKEND_ROOT / ".env")
load_dotenv(_JOURNAL_ROOT / ".env")

# Import directly from the Notion Journal package
sys.path.insert(0, str(_JOURNAL_ROOT))
from src.audio import transcribe
from src.notion_api import NotionJournal
from src.github_backup import JournalBackup
from src import config

router = APIRouter()


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    api_key = config.require("OPENAI_API_KEY")

    suffix = Path(audio.filename or "recording.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await audio.read())
        tmp_path = Path(tmp.name)

    try:
        text = transcribe(tmp_path, api_key)
        return {"transcript": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        tmp_path.unlink(missing_ok=True)


class SaveRequest(BaseModel):
    transcript: str
    entry_date: str = ""


@router.post("/save")
async def save_entry(req: SaveRequest):
    token = config.require("NOTION_TOKEN")
    db_id = config.require("NOTION_DATABASE_ID")

    entry_date = date.fromisoformat(req.entry_date) if req.entry_date else date.today()

    # Split transcript into bullets; fall back to single block if one paragraph
    lines = [l.lstrip("-•* ").strip() for l in req.transcript.splitlines() if l.strip()]
    bullets = lines if lines else [req.transcript]

    journal = NotionJournal(token, db_id)
    result = journal.add_daily_entry(bullets, entry_date)

    # Best-effort git backup (non-fatal)
    gh_token = config.get("GITHUB_TOKEN")
    repo_name = config.get("GITHUB_JOURNAL_REPO")
    if gh_token and repo_name:
        try:
            backup = JournalBackup(gh_token, repo_name)
            backup.commit(
                result["entry_date"],
                result["daily_md"],
                result.get("weekly_md"),
                result.get("monthly_md"),
            )
        except Exception:
            pass

    return {"url": result["daily_url"], "date": result["entry_date"].isoformat()}
