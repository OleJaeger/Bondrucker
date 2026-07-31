"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import health, icons, jobs, presets, preview, printer, settings as settings_api, table, templates
from app.config import get_settings
from app.database import init_db
from app.exceptions import (
    InvalidAttachmentError,
    InvalidJobStateError,
    InvalidMarkdownError,
    JobNotFoundError,
    PresetNotFoundError,
    PresetScriptError,
    TemplateNotFoundError,
)
from app.logging_config import configure_logging
from app.printing.worker import QueueWorker

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()

    worker = QueueWorker()
    worker.recover_interrupted_jobs()
    worker.start()
    app.state.queue_worker = worker

    logger.info("Bondrucker backend started")
    try:
        yield
    finally:
        worker.stop()
        logger.info("Bondrucker backend stopped")


settings = get_settings()

app = FastAPI(
    title="Bondrucker API",
    description=(
        "REST-API zur Verwaltung und Ausfuehrung von ESC/POS-Druckauftraegen "
        "fuer einen netzwerkfaehigen V330M 80mm Thermodrucker."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    openapi_url="/openapi.json" if settings.docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(TemplateNotFoundError)
async def _template_not_found(_request: Request, exc: TemplateNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(InvalidMarkdownError)
async def _invalid_markdown(_request: Request, exc: InvalidMarkdownError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(InvalidAttachmentError)
async def _invalid_attachment(_request: Request, exc: InvalidAttachmentError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(JobNotFoundError)
async def _job_not_found(_request: Request, exc: JobNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(InvalidJobStateError)
async def _invalid_job_state(_request: Request, exc: InvalidJobStateError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(PresetNotFoundError)
async def _preset_not_found(_request: Request, exc: PresetNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(PresetScriptError)
async def _preset_script_error(_request: Request, exc: PresetScriptError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


app.include_router(health.router)
app.include_router(icons.router)
app.include_router(jobs.router)
app.include_router(presets.router)
app.include_router(preview.router)
app.include_router(printer.router)
app.include_router(settings_api.router)
app.include_router(table.router)
app.include_router(templates.router)
