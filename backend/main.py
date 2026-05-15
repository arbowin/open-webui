import os
import sys
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from config import (
    WEBUI_NAME,
    WEBUI_VERSION,
    CORS_ALLOW_ORIGIN,
    SECRET_KEY,
    ENV,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO if ENV == "prod" else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    log.info(f"Starting {WEBUI_NAME} v{WEBUI_VERSION}")
    log.info(f"Environment: {ENV}")
    yield
    log.info(f"Shutting down {WEBUI_NAME}")


app = FastAPI(
    title=WEBUI_NAME,
    version=WEBUI_VERSION,
    docs_url="/docs" if ENV != "prod" else None,
    redoc_url="/redoc" if ENV != "prod" else None,
    lifespan=lifespan,
)

# Session middleware must be added before CORS
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="open-webui-session",
    max_age=30 * 24 * 60 * 60,  # 30 days — extended from 14 for personal convenience
    same_site="lax",
    https_only=(ENV == "prod"),
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGIN,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    log.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {"status": "ok", "version": WEBUI_VERSION}


@app.get("/")
async def root():
    """Root endpoint returning basic application info."""
    return {
        "name": WEBUI_NAME,
        "version": WEBUI_VERSION,
        "description": "Open WebUI — A user-friendly web interface for LLMs",
        # Added environment field so I can quickly confirm which env is running
        # when hitting the root endpoint during local development.
        "environment": ENV,
    }


if __name__ == "__main__":
    import uvicorn

    # Default port changed to 8000 to avoid conflict with other local services on 8080.
    # reload_dirs set explicitly so uvicorn only watches the backend directory,
    # avoiding unnecessary reloads triggered by frontend asset changes.
    # workers=1 is explicit here; bumping to 2 locally causes session issues with
    # in-memory state during development, so keeping it pinned to 1.
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=(ENV != "prod"),
        reload_dirs=["." ] if ENV != "prod" else None,
        workers=1,
    )
