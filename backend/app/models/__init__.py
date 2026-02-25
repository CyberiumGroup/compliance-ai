from app.models.user import User, Role, user_roles
from app.models.framework import CSFFunction, CSFCategory, CSFSubcategory
from app.models.assessment import Assessment, AssessmentStatus
from app.models.policy import Policy, PolicyMapping
from app.models.audit import AuditLog
from app.models.interview import (
    InterviewQuestion,
    InterviewSession,
    InterviewResponse,
    QuestionType,
    InterviewSessionStatus,
)
from app.models.score import SubcategoryScore, CategoryScore, FunctionScore
from app.models.deviation import (
    Deviation,
    DeviationType,
    DeviationSeverity,
    DeviationStatus,
)
from app.models.report import Report, ReportType
from app.models.unified_framework import (
    Framework,
    FrameworkType,
    FrameworkRequirement,
    RequirementCrosswalk,
    MappingType,
    MappingSource,
    RequirementCluster,
    RequirementClusterMember,
    ClusterType,
    CompanyFramework,
    AssessmentFrameworkScope,
)

__all__ = [
    # User & RBAC
    "User",
    "Role",
    "user_roles",
    # Legacy CSF framework (to be deprecated)
    "CSFFunction",
    "CSFCategory",
    "CSFSubcategory",
    # Unified multi-framework support
    "Framework",
    "FrameworkType",
    "FrameworkRequirement",
    "RequirementCrosswalk",
    "MappingType",
    "MappingSource",
    "RequirementCluster",
    "RequirementClusterMember",
    "ClusterType",
    "CompanyFramework",
    "AssessmentFrameworkScope",
    # Assessment
    "Assessment",
    "AssessmentStatus",
    "Policy",
    "PolicyMapping",
    "AuditLog",
    # Interview
    "InterviewQuestion",
    "InterviewSession",
    "InterviewResponse",
    "QuestionType",
    "InterviewSessionStatus",
    # Scoring
    "SubcategoryScore",
    "CategoryScore",
    "FunctionScore",
    # Deviations
    "Deviation",
    "DeviationType",
    "DeviationSeverity",
    "DeviationStatus",
    # Reports
    "Report",
    "ReportType",
]
