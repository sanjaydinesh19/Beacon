from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import journal

app = FastAPI(title="Beacon")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(journal.router, prefix="/api/journal")


@app.get("/api/health")
def health():
    return {"status": "ok"}
