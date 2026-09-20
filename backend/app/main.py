import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.assistant import router as assistant_router
from app.api.health import router as health_router

app = FastAPI(
    title="AI Business Process Assistant API",
    description="Grounded AI business assistant and deterministic analytics API.",
    version="0.3.0",
)

LOCAL_FRONTEND_ORIGINS = {"http://localhost:5173", "http://127.0.0.1:5173"}


def get_frontend_origins() -> list[str]:
    configured = {
        origin.strip().rstrip("/")
        for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
        if origin.strip()
    }
    return sorted(LOCAL_FRONTEND_ORIGINS | configured)


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_frontend_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(analytics_router)
app.include_router(assistant_router)
