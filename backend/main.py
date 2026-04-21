"""FastAPI entrypoint."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.rest import router as rest_router
from backend.api.websocket import router as ws_router

app = FastAPI(title="NAIT CGI Microgrid Digital Twin", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(rest_router)
app.include_router(ws_router)


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}
