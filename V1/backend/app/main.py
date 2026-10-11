from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes_chat, routes_doctors, routes_health, routes_insights, routes_knowledge, routes_tracker
from app.config import get_settings
from app.db.init_db import init_db
from app.logging_config import configure_logging

log = logging.getLogger("sakhisahay")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    log.info(
        "SakhiSahay API ready (env=%s, auth=%s, llm_configured=%s)",
        settings.app_env,
        settings.auth_mode,
        settings.llm_enabled,
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="SakhiSahay API",
        version="0.1.0",
        description="Multilingual, source-grounded women's health companion (mid-semester MVP).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError):
        # Flatten pydantic errors into field -> message pairs the UI can show inline.
        errors = [
            {"field": ".".join(str(p) for p in e.get("loc", []) if p not in ("body", "query")), "message": e.get("msg", "")}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": errors})

    app.include_router(routes_health.router)
    app.include_router(routes_tracker.router)
    app.include_router(routes_insights.router)
    app.include_router(routes_chat.router)
    app.include_router(routes_knowledge.router)
    app.include_router(routes_doctors.router)
    return app


app = create_app()
