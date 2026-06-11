import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Load env: Beacon's own .env first, then fall back to Notion Journal's .env
_BACKEND_ROOT = Path(__file__).parent.parent
_JOURNAL_ROOT = _BACKEND_ROOT.parent.parent / "Notion Journal"

load_dotenv(_BACKEND_ROOT / ".env")
load_dotenv(_JOURNAL_ROOT / ".env")

# Import directly from the Notion Journal package
sys.path.insert(0, str(_JOURNAL_ROOT))
from src.audio import transcribe, bt_switch_hfp, bt_restore_a2dp
from src.formatter import format_transcript
from src.notion_api import NotionJournal
from src.github_backup import JournalBackup
from src import config

router = APIRouter()

# Stored between /bt/hfp and /bt/a2dp calls so the client doesn't need to track IDs.
_bt_state: dict = {}


@router.post("/bt/hfp")
async def switch_bt_hfp():
    """Switch the connected BT headset to HFP so getUserMedia captures the mic."""
    result = bt_switch_hfp()
    if result["found"] and result.get("device_id") is not None:
        _bt_state["device_id"] = result["device_id"]
        _bt_state["a2dp_index"] = result["a2dp_index"]
    return result


@router.post("/bt/a2dp")
async def restore_bt_a2dp():
    """Restore the BT headset to A2DP after recording is done."""
    device_id = _bt_state.get("device_id")
    a2dp_index = _bt_state.get("a2dp_index")
    if device_id is not None and a2dp_index is not None:
        bt_restore_a2dp(device_id, a2dp_index)
        _bt_state.clear()
    return {"restored": device_id is not None}


_DEBUG_AUDIO = Path("/tmp/beacon_last_audio.webm")
_WHISPER_RATE = 16000


def _to_wav(src: Path) -> Path:
    """Convert any audio file to 16kHz mono WAV using ffmpeg."""
    dst = src.with_suffix(".wav")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(src),
         "-ar", str(_WHISPER_RATE), "-ac", "1", "-f", "wav", str(dst)],
        capture_output=True,
    )
    if result.returncode != 0 or not dst.exists():
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.decode()[:300]}")
    return dst


@router.get("/debug/audio")
async def get_debug_audio():
    """Return the last audio blob received from the browser for inspection."""
    if not _DEBUG_AUDIO.exists():
        raise HTTPException(status_code=404, detail="No debug audio saved yet.")
    return FileResponse(_DEBUG_AUDIO, media_type="audio/webm", filename="last_recording.webm")


@router.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    api_key = config.require("OPENAI_API_KEY")

    data = await audio.read()
    suffix = Path(audio.filename or "recording.webm").suffix or ".webm"

    print(f"[transcribe] received {len(data)} bytes, suffix={suffix}")

    # Save a copy for debugging (/api/journal/debug/audio to download).
    _DEBUG_AUDIO.write_bytes(data)

    if len(data) < 1000:
        raise HTTPException(
            status_code=422,
            detail=f"Audio file too small ({len(data)} bytes) — mic may be silent. "
                   "If using Bluetooth headphones, ensure HFP/headset mode is active, not A2DP.",
        )

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        src_path = Path(tmp.name)

    wav_path: Path | None = None
    try:
        wav_path = _to_wav(src_path)
        print(f"[transcribe] converted to WAV: {wav_path.stat().st_size} bytes")
        raw = transcribe(wav_path, api_key)
        bullets = format_transcript(raw, api_key)
        formatted = "\n".join(f"- {b}" for b in bullets)
        return {"transcript": formatted, "raw": raw}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        src_path.unlink(missing_ok=True)
        if wav_path:
            wav_path.unlink(missing_ok=True)


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
