from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.health import router as health_router
from app.api.query import router as query_router
from app.api.report import router as report_router

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """
    Application factory to assemble and configure FastAPI application.
    """
    app = FastAPI(
        title="ComplianceGPT API",
        version="1.0.0",
        description="Backend API for GenAI Cybersecurity Compliance Copilot."
    )

    # Allow frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Routers
    app.include_router(health_router, prefix="/api", tags=["health"])
    app.include_router(query_router, prefix="/api", tags=["query"])
    app.include_router(report_router, prefix="/api", tags=["report"])

    @app.on_event("startup")
    async def startup_event():
        logger.info("ComplianceGPT API starting up...")

    return app

app = create_app()
