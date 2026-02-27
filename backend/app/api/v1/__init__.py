from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.assessments import router as assessments_router
from app.api.v1.policies import router as policies_router
from app.api.v1.mappings import router as mappings_router
from app.api.v1.interviews import router as interviews_router
from app.api.v1.scores import router as scores_router
from app.api.v1.deviations import router as deviations_router
from app.api.v1.reports import router as reports_router
from app.api.v1.framework import router as framework_router
from app.api.v1.frameworks import router as frameworks_router
from app.api.v1.crosswalks import router as crosswalks_router
from app.api.v1.clusters import router as clusters_router

api_router = APIRouter()

# Authentication
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Users
api_router.include_router(users_router, prefix="/users", tags=["users"])

# Dashboard
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

# Existing endpoints
api_router.include_router(assessments_router, prefix="/assessments", tags=["assessments"])
api_router.include_router(policies_router, tags=["policies"])
api_router.include_router(mappings_router, prefix="/mappings", tags=["mappings"])
api_router.include_router(interviews_router, prefix="/interviews", tags=["interviews"])
api_router.include_router(scores_router, prefix="/assessments", tags=["scoring"])
api_router.include_router(deviations_router, tags=["deviations"])
api_router.include_router(reports_router, prefix="/reports", tags=["reports"])
api_router.include_router(framework_router, prefix="/framework", tags=["framework"])

# Multi-framework endpoints
api_router.include_router(frameworks_router, prefix="/frameworks", tags=["frameworks"])
api_router.include_router(crosswalks_router, prefix="/crosswalks", tags=["crosswalks"])
api_router.include_router(clusters_router, prefix="/clusters", tags=["clusters"])
