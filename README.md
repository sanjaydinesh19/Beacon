# Beacon

A private lab hub for my workspace — journal recording, robotics panels, project tracking, and more. Named after the Minecraft block.

Built with SvelteKit + FastAPI, deployable via Docker (Windows) or systemd (Linux).

---

## Features

- **Voice Journal** — Record audio, transcribe with Whisper, format with GPT-4o-mini, review and sync to Notion + GitHub backup
- **Project Dashboard** — Overview of active projects with status and links
- **Robotics Panels** *(planned)* — Telemetry, camera feeds, and simulation viewers for AUV and Quadruped
- **Claude Code Terminal** *(planned)* — Embedded terminal with WebSocket backend

## Stack

| Layer | Tech |
|---|---|
| Frontend | SvelteKit, Vite |
| Backend | FastAPI, Python 3.12 |
| Transcription | OpenAI Whisper |
| Formatting | GPT-4o-mini |
| Sync | Notion API, GitHub API |
| Deployment (Linux) | systemd + nginx + Tailscale |
| Deployment (Windows) | Docker Compose |

## Setup

### Prerequisites

- Python 3.12+
- Node 18+
- ffmpeg
- OpenAI, Notion, and GitHub API keys

### Environment

Copy `.env.example` to `.env` inside `backend/` and fill in your keys:

```
NOTION_TOKEN=
NOTION_DATABASE_ID=
OPENAI_API_KEY=
GITHUB_TOKEN=
GITHUB_JOURNAL_REPO=
SCHEDULER_TIMEZONE=Asia/Kolkata
```

### Linux (systemd)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ..

# Frontend
cd frontend && npm install && cd ..

# Enable services (see .service files in project root)
systemctl --user enable beacon-backend beacon-frontend
systemctl --user start beacon-backend beacon-frontend
```

Access at `http://localhost:5173` or `http://beacon` (with nginx + `/etc/hosts` entry).

### Windows / Docker

```bash
docker compose up --build
```

Access at `http://localhost:5173`.

> Note: Voice recording requires a microphone and runs best outside Docker on Linux due to PipeWire/Bluetooth HFP switching.

## Project Structure

```
Beacon/
├── backend/
│   ├── main.py               # FastAPI app
│   ├── routes/
│   │   └── journal.py        # Journal endpoints
│   ├── notion_journal/       # Reused from Notion Journal project
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte          # Dashboard
│   │   │   └── journal/+page.svelte  # Voice journal
│   │   └── app.css
│   └── vite.config.ts
└── docker-compose.yml
```

## Related

- [Notion Journal](https://github.com/sanjaydinesh19/notion-journal) — standalone journal CLI that Beacon's backend reuses
