# Beacon

A private personal hub — voice journal, GitHub activity, and placement tracker. Named after the Minecraft block.

Built with SvelteKit + FastAPI, deployable via systemd (Linux) or Docker (Windows).

---

## Features

### Voice Journal
Record audio directly in the browser. Beacon transcribes it with Whisper, formats it with GPT-4o-mini, and lets you review before syncing to Notion and a private GitHub repo as a dated Markdown file.

### GitHub Activity
Live feed of recent commits across your repositories, with file diffs and commit messages. Pulls directly from the GitHub API.

### Placement Hub
A placement season tracker built for VIT Chennai campus recruitment.

- **194 companies** across three tiers: Marquee (20+ LPA), Super Dream (10–20 LPA), Dream (<10 LPA)
- Each card shows CTC, domain, eligibility, interview rounds, topics tested, and preparation notes
- **Tier filter pills** — multi-select; defaults to Marquee + Super Dream
- **Kanban tracker** — add any company to your personal tracker with status (watchlist → researching → preparing → ready → applied → interviewed → offered/rejected) and notes
- **Auto-backup** — tracker state commits to a private `beacon-placements` GitHub repo every 6 hours
- **LeetCode daily log** — at 23:00 IST, fetches the day's solved problems (difficulty, topics, links) and commits a dated Markdown to `beacon-placements/lc-daily/`

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | SvelteKit, Vite |
| Backend | FastAPI, Python 3.12 |
| Transcription | OpenAI Whisper |
| Formatting | GPT-4o-mini |
| Sync | Notion API, GitHub API |
| Scheduling | APScheduler (AsyncIOScheduler) |
| Deployment (Linux) | systemd + Tailscale MagicDNS |
| Deployment (Windows) | Docker Compose |

---

## Setup

### Prerequisites

- Python 3.12+
- Node 18+
- ffmpeg (for audio processing)
- API keys: OpenAI, Notion, GitHub

### Environment

Create `backend/.env` with:

```
NOTION_TOKEN=
NOTION_DATABASE_ID=
OPENAI_API_KEY=
GITHUB_TOKEN=
GITHUB_JOURNAL_REPO=username/repo-name
```

The `GITHUB_TOKEN` needs `repo` scope. The placement backup repo (`beacon-placements`) is created automatically on first run if it doesn't exist.

### Linux (systemd)

```bash
# Install dependencies
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../frontend && npm install && cd ..

# Copy and enable service files
cp beacon-backend.service beacon-frontend.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now beacon-backend beacon-frontend
```

Access at `http://localhost:5173`.  
With Tailscale MagicDNS, also reachable at `http://<hostname>.ts.net` across devices.

### Windows / Docker

```bash
docker compose up --build
```

Access at `http://localhost:5173`.

> Voice recording requires a microphone. Works best on Linux; Docker on Windows may have audio limitations.

---

## Usage

### Voice Journal

1. Go to `/journal`
2. Click **Record** — speak your entry
3. Click **Stop** — transcription and formatting run automatically
4. Review the formatted entry in the preview panel
5. Click **Sync** to push to Notion + GitHub

### GitHub Activity

The `/github` page shows your recent commits across all repos. Click any commit to expand the file diff.

### Placement Hub

1. Go to `/placement`
2. Use the **Marquee / Super Dream / Dream** pills to filter by tier (multi-select)
3. Use the search bar to filter by company name or role
4. Click a company card to expand: see CTC, domain, eligibility, interview rounds, topics, and notes
5. Click **Track** on any card to add it to your personal tracker
6. In the tracker panel, update your status and notes as you progress through the recruitment cycle
7. The last backup time is shown in the header — tracker state auto-saves to GitHub every 6 hours

---

## Project Structure

```
Beacon/
├── backend/
│   ├── main.py               # FastAPI app + lifespan (scheduler init)
│   ├── scheduler.py          # APScheduler: 6h backup + 23:00 LC daily log
│   ├── routes/
│   │   ├── journal.py        # Record, transcribe, format, sync
│   │   ├── github.py         # Commit feed
│   │   └── placement.py      # Companies, tracker CRUD
│   ├── data/
│   │   ├── companies.json    # 194 companies with full interview details
│   │   └── tracker.json      # Personal tracker state (gitignored)
│   ├── notion_journal/       # Shared Notion/GitHub sync utilities
│   └── requirements.txt
├── frontend/
│   └── src/routes/
│       ├── +page.svelte              # Dashboard
│       ├── journal/+page.svelte      # Voice journal
│       ├── github/+page.svelte       # Activity feed
│       └── placement/+page.svelte    # Placement hub
└── docker-compose.yml
```

---

## Related

- [Notion Journal](https://github.com/sanjaydinesh19/notion-journal) — standalone CLI that Beacon's backend reuses for journal sync
