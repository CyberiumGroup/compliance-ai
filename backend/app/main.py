import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.v1 import api_router
from app.core.config import settings
from app.db.session import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load built-in frameworks on startup
    db = SessionLocal()
    try:
        from app.services.frameworks.framework_service import FrameworkService
        service = FrameworkService(db)
        service.load_all_builtin_frameworks(force_reload=False)
    except Exception as e:
        print(f"Warning: Failed to load built-in frameworks: {e}")
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    description="AI-driven multi-framework compliance assessment engine",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check (no prefix)
app.include_router(health_router, tags=["health"])

# API v1 routes
app.include_router(api_router, prefix=settings.api_v1_prefix)
