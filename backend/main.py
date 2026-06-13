import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import journal, github, placement

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    from scheduler import ensure_backup_repo, init_scheduler, shutdown_scheduler
    ensure_backup_repo()
    init_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Beacon", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(journal.router, prefix="/api/journal")
app.include_router(github.router, prefix="/api/github")
app.include_router(placement.router, prefix="/api/placement")


@app.get("/api/health")
def health():
    return {"status": "ok"}
