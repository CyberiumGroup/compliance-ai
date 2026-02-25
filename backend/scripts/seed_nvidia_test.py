"""
Comprehensive test data seeding script for "Nvidia Inc" assessment.

Creates realistic data across 4 frameworks (NIST CSF, ISO 27001, SOC 2, custom NVIDIA standards),
multiple interview sessions, and full scoring/deviation detection.

Usage:
    cd backend
    python -m scripts.seed_nvidia_test
    python -m scripts.seed_nvidia_test --clean
    python -m scripts.seed_nvidia_test --skip-interviews --skip-scoring
"""

import argparse
import random
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.assessment import Assessment
from app.models.policy import Policy, PolicyMapping
from app.models.interview import (
    InterviewSession, InterviewQuestion, InterviewResponse,
    InterviewSessionStatus, QuestionType,
)
from app.models.unified_framework import (
    Framework, FrameworkRequirement, FrameworkType,
    CompanyFramework, AssessmentFrameworkScope,
)
from app.models.framework import CSFSubcategory
from app.models.user import User
from app.models.deviation import Deviation
from app.models.score import SubcategoryScore, CategoryScore, FunctionScore
from app.services.frameworks.framework_service import FrameworkService
from app.services.scoring.scoring_engine import ScoringEngine
from app.services.deviation.detector import DeviationDetector


# ============================================================================
# NVIDIA Personnel Data
# ============================================================================

NVIDIA_PERSONNEL = [
    {
        "name": "Sarah Chen",
        "role": "CISO",
        "email": "sarah.chen@nvidia.com",
        "focus_areas": ["governance", "strategy", "risk_management", "executive"],
    },
    {
        "name": "Michael Rodriguez",
        "role": "VP of Engineering",
        "email": "michael.rodriguez@nvidia.com",
        "focus_areas": ["development", "technical_controls", "sdlc", "architecture"],
    },
    {
        "name": "Jennifer Walsh",
        "role": "Director of IT Operations",
        "email": "jennifer.walsh@nvidia.com",
        "focus_areas": ["operations", "change_management", "monitoring", "incident"],
    },
    {
        "name": "David Park",
        "role": "Cloud Security Architect",
        "email": "david.park@nvidia.com",
        "focus_areas": ["cloud", "infrastructure", "network", "architecture"],
    },
    {
        "name": "Amanda Foster",
        "role": "Compliance Manager",
        "email": "amanda.foster@nvidia.com",
        "focus_areas": ["compliance", "audit", "documentation", "policy"],
    },
    {
        "name": "Robert Kim",
        "role": "Data Protection Officer",
        "email": "robert.kim@nvidia.com",
        "focus_areas": ["data_protection", "privacy", "classification", "retention"],
    },
]


# ============================================================================
# Custom NVIDIA Framework Definition
# ============================================================================

NVIDIA_FRAMEWORK = {
    "code": "NVIDIA-SEC-2024",
    "name": "NVIDIA Security Standards",
    "version": "2024.1",
    "description": "Internal security standards for NVIDIA Corporation covering GPU security, AI/ML data protection, and supply chain requirements.",
    "hierarchy_labels": ["Domain", "Control Area", "Requirement"],
    "domains": [
        {
            "code": "GPU-SEC",
            "name": "GPU Security",
            "description": "Security controls for GPU hardware and firmware",
            "requirements": [
                {"code": "GPU-SEC-01", "name": "GPU Firmware Integrity", "description": "Ensure GPU firmware is cryptographically signed and verified at boot"},
                {"code": "GPU-SEC-02", "name": "GPU Memory Protection", "description": "Implement memory isolation for multi-tenant GPU workloads"},
                {"code": "GPU-SEC-03", "name": "GPU Driver Security", "description": "Maintain secure GPU driver development and update processes"},
                {"code": "GPU-SEC-04", "name": "GPU Access Control", "description": "Implement role-based access controls for GPU resources"},
                {"code": "GPU-SEC-05", "name": "GPU Audit Logging", "description": "Enable comprehensive audit logging for GPU operations"},
                {"code": "GPU-SEC-06", "name": "GPU Vulnerability Management", "description": "Establish processes for GPU-specific vulnerability identification and remediation"},
            ],
        },
        {
            "code": "AI-DP",
            "name": "AI/ML Data Protection",
            "description": "Data protection requirements for AI and machine learning workloads",
            "requirements": [
                {"code": "AI-DP-01", "name": "Training Data Classification", "description": "Classify and label all AI/ML training datasets according to sensitivity"},
                {"code": "AI-DP-02", "name": "Model Security", "description": "Protect AI/ML models as intellectual property with appropriate access controls"},
                {"code": "AI-DP-03", "name": "Inference Data Protection", "description": "Secure data during AI inference operations"},
                {"code": "AI-DP-04", "name": "Data Lineage Tracking", "description": "Maintain complete lineage tracking for training data"},
                {"code": "AI-DP-05", "name": "Model Versioning", "description": "Implement secure versioning and rollback capabilities for models"},
                {"code": "AI-DP-06", "name": "Bias Detection", "description": "Implement automated bias detection in AI/ML pipelines"},
            ],
        },
        {
            "code": "SC-SEC",
            "name": "Supply Chain Security",
            "description": "Security requirements for hardware and software supply chain",
            "requirements": [
                {"code": "SC-SEC-01", "name": "Supplier Assessment", "description": "Conduct security assessments of critical suppliers"},
                {"code": "SC-SEC-02", "name": "Component Verification", "description": "Verify authenticity of hardware components"},
                {"code": "SC-SEC-03", "name": "Software Bill of Materials", "description": "Maintain SBOM for all software products"},
                {"code": "SC-SEC-04", "name": "Secure Manufacturing", "description": "Implement security controls in manufacturing facilities"},
                {"code": "SC-SEC-05", "name": "Distribution Security", "description": "Secure product distribution and chain of custody"},
                {"code": "SC-SEC-06", "name": "Counterfeit Prevention", "description": "Implement counterfeit detection and prevention measures"},
            ],
        },
        {
            "code": "CLOUD",
            "name": "Cloud Infrastructure",
            "description": "Cloud security requirements for NVIDIA services",
            "requirements": [
                {"code": "CLOUD-01", "name": "Cloud Provider Assessment", "description": "Assess security posture of cloud service providers"},
                {"code": "CLOUD-02", "name": "Cloud Workload Protection", "description": "Implement workload protection for cloud deployments"},
                {"code": "CLOUD-03", "name": "Cloud Access Management", "description": "Implement IAM controls for cloud resources"},
                {"code": "CLOUD-04", "name": "Cloud Network Security", "description": "Implement network segmentation and security in cloud environments"},
                {"code": "CLOUD-05", "name": "Cloud Data Encryption", "description": "Encrypt data at rest and in transit in cloud environments"},
                {"code": "CLOUD-06", "name": "Cloud Monitoring", "description": "Implement comprehensive monitoring and alerting for cloud resources"},
            ],
        },
        {
            "code": "EP-SEC",
            "name": "Endpoint Protection",
            "description": "Endpoint security requirements",
            "requirements": [
                {"code": "EP-SEC-01", "name": "Endpoint Detection and Response", "description": "Deploy EDR solutions on all corporate endpoints"},
                {"code": "EP-SEC-02", "name": "Endpoint Encryption", "description": "Implement full disk encryption on all endpoints"},
                {"code": "EP-SEC-03", "name": "Patch Management", "description": "Maintain timely patch deployment for endpoints"},
                {"code": "EP-SEC-04", "name": "Mobile Device Management", "description": "Implement MDM for corporate mobile devices"},
                {"code": "EP-SEC-05", "name": "Endpoint Configuration", "description": "Maintain secure baseline configurations for endpoints"},
                {"code": "EP-SEC-06", "name": "Removable Media Control", "description": "Control use of removable media on endpoints"},
            ],
        },
        {
            "code": "IAM",
            "name": "Identity Management",
            "description": "Identity and access management requirements",
            "requirements": [
                {"code": "IAM-01", "name": "Identity Lifecycle Management", "description": "Implement automated identity provisioning and deprovisioning"},
                {"code": "IAM-02", "name": "Multi-Factor Authentication", "description": "Require MFA for all user accounts"},
                {"code": "IAM-03", "name": "Privileged Access Management", "description": "Implement PAM controls for administrative access"},
                {"code": "IAM-04", "name": "Access Reviews", "description": "Conduct periodic access certification reviews"},
                {"code": "IAM-05", "name": "Single Sign-On", "description": "Implement SSO for corporate applications"},
                {"code": "IAM-06", "name": "Service Account Management", "description": "Manage and secure service accounts"},
            ],
        },
        {
            "code": "IR",
            "name": "Incident Response",
            "description": "Incident response and management requirements",
            "requirements": [
                {"code": "IR-01", "name": "Incident Response Plan", "description": "Maintain documented incident response procedures"},
                {"code": "IR-02", "name": "Incident Detection", "description": "Implement automated incident detection capabilities"},
                {"code": "IR-03", "name": "Incident Classification", "description": "Define incident severity classifications and escalation paths"},
                {"code": "IR-04", "name": "Forensic Capability", "description": "Maintain digital forensics capabilities"},
                {"code": "IR-05", "name": "Incident Communication", "description": "Establish incident communication protocols"},
                {"code": "IR-06", "name": "Post-Incident Review", "description": "Conduct post-incident reviews and implement lessons learned"},
            ],
        },
        {
            "code": "COMP",
            "name": "Compliance & Audit",
            "description": "Compliance and audit requirements",
            "requirements": [
                {"code": "COMP-01", "name": "Regulatory Tracking", "description": "Track applicable regulatory requirements"},
                {"code": "COMP-02", "name": "Compliance Monitoring", "description": "Implement continuous compliance monitoring"},
                {"code": "COMP-03", "name": "Audit Trail", "description": "Maintain comprehensive audit trails"},
                {"code": "COMP-04", "name": "Evidence Collection", "description": "Automate evidence collection for audits"},
                {"code": "COMP-05", "name": "Third-Party Assessments", "description": "Conduct periodic third-party security assessments"},
                {"code": "COMP-06", "name": "Exception Management", "description": "Implement formal exception and waiver processes"},
            ],
        },
    ],
}



# ============================================================================
# Policy Definitions (12 policies)
# ============================================================================

POLICIES = [
    {
        "name": "Information Security Policy",
        "code": "ISP",
        "description": "Enterprise-wide information security policy establishing security objectives and responsibilities",
        "version": "4.2",
        "owner": "Sarah Chen, CISO",
    },
    {
        "name": "Access Control Policy",
        "code": "ACP",
        "description": "Policy governing user access management, authentication, and authorization",
        "version": "3.1",
        "owner": "Sarah Chen, CISO",
    },
    {
        "name": "Data Classification and Protection Policy",
        "code": "DCP",
        "description": "Policy for classifying and protecting data based on sensitivity",
        "version": "2.5",
        "owner": "Robert Kim, DPO",
    },
    {
        "name": "Incident Response Policy",
        "code": "IRP",
        "description": "Policy for detecting, responding to, and recovering from security incidents",
        "version": "3.0",
        "owner": "Jennifer Walsh, Director IT Ops",
    },
    {
        "name": "Business Continuity Policy",
        "code": "BCP",
        "description": "Policy for maintaining operations during disruptions",
        "version": "2.3",
        "owner": "Jennifer Walsh, Director IT Ops",
    },
    {
        "name": "Acceptable Use Policy",
        "code": "AUP",
        "description": "Policy governing acceptable use of company IT resources",
        "version": "5.0",
        "owner": "Sarah Chen, CISO",
    },
    {
        "name": "Encryption and Key Management Policy",
        "code": "EKM",
        "description": "Policy for cryptographic controls and key management",
        "version": "2.1",
        "owner": "David Park, Cloud Security Architect",
    },
    {
        "name": "Network Security Policy",
        "code": "NSP",
        "description": "Policy for network security architecture and controls",
        "version": "3.2",
        "owner": "David Park, Cloud Security Architect",
    },
    {
        "name": "Vendor and Third-Party Security Policy",
        "code": "VTP",
        "description": "Policy for managing security risks from vendors and third parties",
        "version": "2.0",
        "owner": "Amanda Foster, Compliance Manager",
    },
    {
        "name": "Physical Security Policy",
        "code": "PSP",
        "description": "Policy for physical access controls and facility security",
        "version": "2.4",
        "owner": "Jennifer Walsh, Director IT Ops",
    },
    {
        "name": "Change Management Policy",
        "code": "CMP",
        "description": "Policy for managing changes to IT systems and infrastructure",
        "version": "3.1",
        "owner": "Michael Rodriguez, VP Engineering",
    },
    {
        "name": "Cloud Security Policy",
        "code": "CSP",
        "description": "Policy for securing cloud infrastructure and services",
        "version": "2.0",
        "owner": "David Park, Cloud Security Architect",
    },
]


# ============================================================================
# Interview Response Templates
# ============================================================================

YES_RESPONSE_TEMPLATES = [
    "Yes, we have {topic} fully implemented. {detail}",
    "Absolutely. {topic} has been in place since {year}. {detail}",
    "Yes, this is a core part of our security program. {detail}",
    "Confirmed. We implemented {topic} as part of our {initiative}. {detail}",
    "Yes, we use {tool} for {topic}. {detail}",
]

PARTIAL_RESPONSE_TEMPLATES = [
    "Partially. We have {topic} implemented for {scope}, but {gap}.",
    "We're in progress on this. {topic} is about {percent}% complete. {remaining}",
    "We have {topic} for critical systems, but {gap} for lower-risk systems.",
    "Yes for {scope}, but we still need to address {gap}.",
    "This is implemented in some areas. {detail} However, {gap}.",
]

NO_RESPONSE_TEMPLATES = [
    "Not currently. {topic} is planned for {timeline}.",
    "No, but it's on our roadmap. We expect to implement {topic} in {timeline}.",
    "This is a gap we've identified. {topic} is prioritized for {timeline}.",
    "We don't have {topic} yet. Resource constraints have delayed this. Target: {timeline}.",
    "No formal {topic} exists. We're working with {team} to develop this by {timeline}.",
]


RESPONSE_DETAILS = {
    "governance": {
        "yes": [
            "Our security governance framework is aligned with NIST CSF 2.0 and reviewed quarterly by the board.",
            "We have an established security steering committee that meets monthly.",
            "Security KPIs are tracked and reported to the executive team weekly.",
        ],
        "partial": [
            "Governance policies exist but need updates for our recent cloud expansion.",
            "The framework is documented but enforcement is inconsistent across business units.",
        ],
        "no": [
            "We're building out formal governance with external consultants.",
            "This is being developed as part of our security transformation initiative.",
        ],
    },
    "access_control": {
        "yes": [
            "We use Okta for enterprise IAM with 100% MFA coverage for all users.",
            "Access reviews are conducted quarterly with automated certification workflows.",
            "Our PAM solution from CyberArk manages all privileged access.",
        ],
        "partial": [
            "MFA is implemented for 85% of users, with legacy systems being migrated.",
            "Access reviews are manual for some legacy systems.",
        ],
        "no": [
            "We're evaluating Okta and Ping Identity for enterprise IAM.",
            "Budget approved for Q2 implementation.",
        ],
    },
    "network": {
        "yes": [
            "Zero trust architecture implemented with Zscaler and Palo Alto.",
            "Network segmentation follows our data classification scheme.",
            "All traffic is encrypted with TLS 1.3 minimum.",
        ],
        "partial": [
            "Segmentation implemented for production but development networks need work.",
            "Zero trust rollout is 70% complete.",
        ],
        "no": [
            "Network redesign project kicks off next quarter.",
            "We're migrating to a SASE architecture.",
        ],
    },
    "data_protection": {
        "yes": [
            "All data is classified and labeled according to our 4-tier scheme.",
            "DLP is deployed across all endpoints and cloud applications.",
            "Encryption at rest and in transit is enforced for all sensitive data.",
        ],
        "partial": [
            "DLP covers email and endpoints but cloud coverage is being expanded.",
            "Data classification exists but labeling automation is still being deployed.",
        ],
        "no": [
            "DLP tool selection is underway with POCs from Microsoft and Symantec.",
            "Data classification project starting in Q3.",
        ],
    },
    "incident_response": {
        "yes": [
            "24/7 SOC with automated playbooks in Splunk SOAR.",
            "Tabletop exercises conducted quarterly with executive participation.",
            "Mean time to detect is under 30 minutes for critical incidents.",
        ],
        "partial": [
            "SOC covers business hours; after-hours is on-call rotation.",
            "Playbooks exist for common scenarios but need expansion.",
        ],
        "no": [
            "SOC buildout in progress with target go-live in Q2.",
            "Currently relying on MSSP for incident response.",
        ],
    },
    "cloud": {
        "yes": [
            "Cloud Security Posture Management deployed across AWS, Azure, and GCP.",
            "Infrastructure as Code with security scanning in CI/CD pipelines.",
            "Cloud access is managed through centralized IAM with just-in-time access.",
        ],
        "partial": [
            "CSPM covers AWS and Azure; GCP migration underway.",
            "Some legacy cloud workloads don't follow current standards.",
        ],
        "no": [
            "Cloud security program being developed alongside cloud migration.",
            "Currently evaluating Wiz and Orca for CSPM.",
        ],
    },
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_or_create_user(db: Session, email: str, name: str) -> User:
    """Get or create a user by email."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            id=uuid.uuid4(),
            email=email,
            name=name,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()
    return user


def generate_response_text(
    response_type: str,
    question_type: str,
    topic: str | None = None,
) -> tuple[str, str]:
    """Generate realistic response text based on response type."""
    topic = topic or "this control"

    if response_type == "yes":
        templates = YES_RESPONSE_TEMPLATES
        details = RESPONSE_DETAILS.get(
            random.choice(list(RESPONSE_DETAILS.keys())), {}
        ).get("yes", ["This is fully implemented and documented."])
    elif response_type == "partial":
        templates = PARTIAL_RESPONSE_TEMPLATES
        details = ["We're working on expanding coverage."]
    else:
        templates = NO_RESPONSE_TEMPLATES
        details = ["Target implementation is within the next two quarters."]

    template = random.choice(templates)
    detail = random.choice(details)

    # Fill in template variables
    text = template.format(
        topic=topic,
        detail=detail,
        year=random.choice(["2022", "2023", "early 2024"]),
        initiative=random.choice(["security transformation", "compliance program", "cloud migration"]),
        tool=random.choice(["Okta", "CrowdStrike", "Splunk", "Palo Alto", "Wiz"]),
        scope=random.choice(["production systems", "cloud workloads", "critical assets"]),
        gap=random.choice([
            "legacy systems still need migration",
            "some business units haven't fully adopted",
            "documentation needs updating",
        ]),
        percent=random.choice([60, 70, 75, 80, 85]),
        remaining=random.choice([
            "Remaining work is scheduled for next quarter.",
            "We expect full completion within 90 days.",
        ]),
        timeline=random.choice(["Q2 2024", "Q3 2024", "end of year", "next quarter"]),
        team=random.choice(["security team", "compliance", "IT operations"]),
    )

    # Generate confidence level based on response type
    if response_type == "yes":
        confidence = random.choice(["high", "high", "high", "medium"])
    elif response_type == "partial":
        confidence = random.choice(["medium", "medium", "low"])
    else:
        confidence = "high"  # Confident about the "no"

    return text, confidence


def clean_nvidia_data(db: Session) -> None:
    """Remove existing Nvidia Inc assessment and related data."""
    print("Cleaning existing Nvidia Inc data...")

    # Find Nvidia assessment
    assessment = db.query(Assessment).filter(
        Assessment.organization_name == "Nvidia Inc"
    ).first()

    if assessment:
        # Delete in order to respect foreign keys
        db.query(Deviation).filter(
            Deviation.assessment_id == assessment.id
        ).delete()

        db.query(FunctionScore).filter(
            FunctionScore.assessment_id == assessment.id
        ).delete()

        db.query(CategoryScore).filter(
            CategoryScore.assessment_id == assessment.id
        ).delete()

        db.query(SubcategoryScore).filter(
            SubcategoryScore.assessment_id == assessment.id
        ).delete()

        # Delete interview responses and sessions
        sessions = db.query(InterviewSession).filter(
            InterviewSession.assessment_id == assessment.id
        ).all()
        for session in sessions:
            db.query(InterviewResponse).filter(
                InterviewResponse.session_id == session.id
            ).delete()

        db.query(InterviewSession).filter(
            InterviewSession.assessment_id == assessment.id
        ).delete()

        # Delete mappings and related entities
        policies = db.query(Policy).filter(
            Policy.assessment_id == assessment.id
        ).all()
        for policy in policies:
            db.query(PolicyMapping).filter(
                PolicyMapping.policy_id == policy.id
            ).delete()

        db.query(Policy).filter(
            Policy.assessment_id == assessment.id
        ).delete()

        # Delete assessment scope
        db.query(AssessmentFrameworkScope).filter(
            AssessmentFrameworkScope.assessment_id == assessment.id
        ).delete()

        # Delete company frameworks for Nvidia
        db.query(CompanyFramework).filter(
            CompanyFramework.organization_name == "Nvidia Inc"
        ).delete()

        # Delete assessment
        db.delete(assessment)

        print(f"  Deleted assessment: {assessment.id}")

    # Delete NVIDIA custom framework
    nvidia_framework = db.query(Framework).filter(
        Framework.code == "NVIDIA-SEC-2024"
    ).first()

    if nvidia_framework:
        # Delete requirements
        db.query(FrameworkRequirement).filter(
            FrameworkRequirement.framework_id == nvidia_framework.id
        ).delete()

        db.delete(nvidia_framework)
        print(f"  Deleted framework: NVIDIA-SEC-2024")

    db.commit()
    print("Cleanup complete.")


# ============================================================================
# Main Seeding Functions
# ============================================================================

def load_builtin_frameworks(db: Session) -> dict[str, Framework]:
    """Load built-in frameworks (NIST, ISO, SOC2)."""
    print("\n1. Loading built-in frameworks...")

    framework_service = FrameworkService(db)
    frameworks = {}

    for framework_type in [FrameworkType.NIST_CSF, FrameworkType.ISO_27001, FrameworkType.SOC2_TSC]:
        try:
            framework = framework_service.load_builtin_framework(framework_type.value)
            frameworks[framework_type.value] = framework
            print(f"   Loaded: {framework.name} ({framework.code})")
        except Exception as e:
            # Framework may already exist
            existing = framework_service.get_framework_by_code(
                f"NIST-CSF-2.0" if framework_type == FrameworkType.NIST_CSF
                else f"ISO-27001-2022" if framework_type == FrameworkType.ISO_27001
                else "SOC2-TSC"
            )
            if existing:
                frameworks[framework_type.value] = existing
                print(f"   Found existing: {existing.name} ({existing.code})")
            else:
                print(f"   Warning: Could not load {framework_type.value}: {e}")

    return frameworks


def create_nvidia_framework(db: Session) -> Framework:
    """Create custom NVIDIA Security Standards framework."""
    print("\n2. Creating NVIDIA custom framework...")

    # Check if already exists
    existing = db.query(Framework).filter(Framework.code == NVIDIA_FRAMEWORK["code"]).first()
    if existing:
        print(f"   Found existing: {existing.name}")
        return existing

    framework = Framework(
        id=uuid.uuid4(),
        code=NVIDIA_FRAMEWORK["code"],
        name=NVIDIA_FRAMEWORK["name"],
        version=NVIDIA_FRAMEWORK["version"],
        description=NVIDIA_FRAMEWORK["description"],
        framework_type=FrameworkType.CUSTOM.value,
        hierarchy_levels=3,
        hierarchy_labels=NVIDIA_FRAMEWORK["hierarchy_labels"],
        is_active=True,
        is_builtin=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(framework)
    db.flush()

    # Create domains and requirements
    for idx, domain in enumerate(NVIDIA_FRAMEWORK["domains"]):
        domain_req = FrameworkRequirement(
            id=uuid.uuid4(),
            framework_id=framework.id,
            parent_id=None,
            code=domain["code"],
            name=domain["name"],
            description=domain["description"],
            level=0,
            is_assessable=False,
            display_order=idx,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(domain_req)
        db.flush()

        for req_idx, req in enumerate(domain["requirements"]):
            requirement = FrameworkRequirement(
                id=uuid.uuid4(),
                framework_id=framework.id,
                parent_id=domain_req.id,
                code=req["code"],
                name=req["name"],
                description=req["description"],
                level=1,
                is_assessable=True,
                display_order=req_idx,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(requirement)

    db.flush()
    print(f"   Created: {framework.name} with {len(NVIDIA_FRAMEWORK['domains'])} domains, 48 requirements")

    return framework


def create_nvidia_assessment(db: Session, user: User) -> Assessment:
    """Create Nvidia Inc assessment."""
    print("\n3. Creating Nvidia Inc assessment...")

    assessment = Assessment(
        id=uuid.uuid4(),
        name="NVIDIA 2024 Security Assessment",
        description="Comprehensive security assessment for NVIDIA Corporation covering NIST CSF 2.0, ISO 27001:2022, SOC 2, and internal NVIDIA Security Standards.",
        organization_name="Nvidia Inc",
        status="draft",
        created_by_id=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(assessment)
    db.flush()

    print(f"   Created assessment: {assessment.id}")
    return assessment


def set_assessment_scope(
    db: Session,
    assessment: Assessment,
    frameworks: dict[str, Framework],
    nvidia_framework: Framework,
) -> None:
    """Set framework scope for assessment."""
    print("\n4. Setting assessment framework scope...")

    # Add all frameworks to scope
    all_frameworks = list(frameworks.values()) + [nvidia_framework]

    for idx, framework in enumerate(all_frameworks):
        # Add company framework association
        company_fw = CompanyFramework(
            id=uuid.uuid4(),
            organization_name="Nvidia Inc",
            framework_id=framework.id,
            is_active=True,
            priority=idx,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(company_fw)

        # Add assessment scope
        scope = AssessmentFrameworkScope(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            framework_id=framework.id,
            include_all=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(scope)
        print(f"   Added scope: {framework.code}")

    db.flush()


def create_policies(db: Session, assessment: Assessment) -> list[Policy]:
    """Create 12 policies for the assessment."""
    print("\n6. Creating policies...")

    policies = []

    for policy_data in POLICIES:
        content = f"""# {policy_data['name']}

## Purpose
This policy establishes {policy_data['description'].lower()}.

## Scope
This policy applies to all NVIDIA employees, contractors, and third parties with access to NVIDIA systems and data.

## Policy Statements
1. All users must comply with security requirements outlined in this policy.
2. Violations may result in disciplinary action up to and including termination.
3. Exceptions must be approved through the formal exception process.

## Responsibilities
- **CISO**: Overall accountability for policy enforcement
- **Policy Owner ({policy_data['owner']})**: Maintenance and updates
- **All Employees**: Compliance with policy requirements

## Review
This policy is reviewed annually and updated as needed.

Version: {policy_data['version']}
Last Updated: {datetime.utcnow().strftime('%Y-%m-%d')}
"""

        policy = Policy(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            name=policy_data["name"],
            description=policy_data["description"],
            version=policy_data["version"],
            owner=policy_data["owner"],
            content_text=content,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(policy)
        policies.append(policy)

    db.flush()
    print(f"   Created {len(policies)} policies")

    return policies


def create_mappings(
    db: Session,
    policies: list[Policy],
) -> int:
    """Create policy mappings to subcategories."""
    print("\n6. Creating policy mappings...")

    # Get all subcategories
    subcategories = db.query(CSFSubcategory).all()
    subcat_map = {s.code: s for s in subcategories}

    policy_mapping_count = 0

    policy_to_subcat = {
        "ISP": ["GV.PO", "GV.OV", "GV.RM"],
        "ACP": ["PR.AA", "PR.AC"],
        "DCP": ["PR.DS", "ID.AM"],
        "IRP": ["RS.RP", "RS.CO", "RS.AN"],
        "BCP": ["PR.IP", "RC.RP", "RC.CO"],
        "AUP": ["PR.AT", "GV.PO"],
        "EKM": ["PR.DS"],
        "NSP": ["PR.AC", "PR.DS", "DE.CM"],
        "VTP": ["ID.SC"],
        "PSP": ["PR.AC", "PR.PT"],
        "CMP": ["PR.IP", "PR.MA"],
        "CSP": ["PR.DS", "PR.AC", "PR.PT"],
    }

    for policy in policies:
        code = policy.name.split()[0][:3].upper()
        if code == "INF":
            code = "ISP"
        elif code == "ACC":
            code = "ACP"
        elif code == "DAT":
            code = "DCP"
        elif code == "INC":
            code = "IRP"
        elif code == "BUS":
            code = "BCP"
        elif code == "ENC":
            code = "EKM"
        elif code == "NET":
            code = "NSP"
        elif code == "VEN":
            code = "VTP"
        elif code == "PHY":
            code = "PSP"
        elif code == "CHA":
            code = "CMP"
        elif code == "CLO":
            code = "CSP"

        subcat_prefixes = policy_to_subcat.get(code, ["GV.PO"])

        for subcat_prefix in subcat_prefixes:
            matching = [s for code, s in subcat_map.items() if code.startswith(subcat_prefix)]
            for subcat in matching[:2]:  # Map to up to 2 subcategories
                mapping = PolicyMapping(
                    id=uuid.uuid4(),
                    policy_id=policy.id,
                    subcategory_id=subcat.id,
                    confidence_score=random.uniform(0.80, 0.98),
                    is_approved=random.random() > 0.1,  # 90% approved
                    created_at=datetime.utcnow(),
                )
                db.add(mapping)
                policy_mapping_count += 1

    db.flush()
    print(f"   Created {policy_mapping_count} policy mappings")

    return policy_mapping_count


def create_interview_sessions(
    db: Session,
    assessment: Assessment,
) -> list[InterviewSession]:
    """Create 6 interview sessions with different personnel."""
    print("\n8. Creating interview sessions...")

    sessions = []

    for idx, person in enumerate(NVIDIA_PERSONNEL):
        # Create or get user for interviewee
        user = get_or_create_user(db, person["email"], person["name"])

        session = InterviewSession(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            interviewee_id=user.id,
            interviewee_name=person["name"],
            interviewee_role=person["role"],
            status=InterviewSessionStatus.COMPLETED.value,
            current_question_index=0,
            total_questions=25,  # Will be updated
            started_at=datetime.utcnow() - timedelta(days=7 - idx),
            completed_at=datetime.utcnow() - timedelta(days=6 - idx),
            created_at=datetime.utcnow() - timedelta(days=7 - idx),
            updated_at=datetime.utcnow() - timedelta(days=6 - idx),
            notes=f"Interview with {person['name']}, {person['role']}. Focus areas: {', '.join(person['focus_areas'])}",
        )
        db.add(session)
        sessions.append((session, person))

    db.flush()
    print(f"   Created {len(sessions)} interview sessions")

    return sessions


def create_interview_responses(
    db: Session,
    sessions: list[tuple[InterviewSession, dict]],
) -> int:
    """Create ~150 interview responses across sessions."""
    print("\n9. Creating interview responses...")

    # Get all interview questions
    questions = db.query(InterviewQuestion).filter(
        InterviewQuestion.is_active == True
    ).all()

    if not questions:
        print("   Warning: No interview questions found. Skipping responses.")
        return 0

    response_count = 0

    # Response distribution: 55% yes, 30% partial, 15% no
    response_types = ["yes"] * 55 + ["partial"] * 30 + ["no"] * 15

    # Assign questions to sessions based on focus areas
    questions_per_session = len(questions) // len(sessions) + 5

    for session, person in sessions:
        # Select questions relevant to this person's focus areas
        session_questions = random.sample(
            questions,
            min(questions_per_session, len(questions))
        )

        for question in session_questions:
            response_type = random.choice(response_types)
            response_text, confidence = generate_response_text(
                response_type,
                question.question_type,
                topic=question.question_text[:50] if question.question_text else "this control",
            )

            response = InterviewResponse(
                id=uuid.uuid4(),
                session_id=session.id,
                question_id=question.id,
                response_text=response_text,
                response_value=response_type,
                confidence_level=confidence,
                evidence_references={
                    "documents": [f"DOC-{random.randint(100, 999)}"] if response_type == "yes" else [],
                    "systems": [f"SYS-{random.randint(100, 999)}"] if response_type in ["yes", "partial"] else [],
                },
                responded_at=session.started_at + timedelta(minutes=random.randint(5, 120)),
                created_at=session.started_at + timedelta(minutes=random.randint(5, 120)),
            )
            db.add(response)
            response_count += 1

        # Update session totals
        session.total_questions = len(session_questions)
        session.current_question_index = len(session_questions)

    db.flush()
    print(f"   Created {response_count} interview responses")

    return response_count


def calculate_scores(db: Session, assessment: Assessment) -> dict[str, Any]:
    """Calculate scores using ScoringEngine."""
    print("\n10. Calculating scores...")

    scoring_engine = ScoringEngine(db)
    results = scoring_engine.calculate_all_scores(assessment.id)

    print(f"   Overall maturity: {results['overall_maturity']}")
    print(f"   Function scores calculated: {len(results['function_scores'])}")

    return results


def detect_deviations(db: Session, assessment: Assessment) -> list[dict]:
    """Detect deviations using DeviationDetector."""
    print("\n11. Detecting deviations...")

    detector = DeviationDetector(db)
    deviations = detector.detect_all_deviations(assessment.id)

    # Count by severity
    severity_counts = {}
    for dev in deviations:
        severity = dev.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    print(f"   Total deviations: {len(deviations)}")
    for severity, count in sorted(severity_counts.items()):
        print(f"   - {severity}: {count}")

    return deviations


def update_assessment_status(db: Session, assessment: Assessment) -> None:
    """Update assessment status to 'review'."""
    print("\n12. Updating assessment status...")

    assessment.status = "review"
    assessment.updated_at = datetime.utcnow()
    db.flush()

    print(f"   Status updated to: {assessment.status}")


def print_summary(
    assessment: Assessment,
    policies: list[Policy],
    sessions: list,
    response_count: int,
    deviations: list[dict],
) -> None:
    """Print final summary."""
    print("\n" + "=" * 60)
    print("=== Nvidia Inc Test Data Seeding Complete ===")
    print("=" * 60)
    print(f"Assessment ID: {assessment.id}")
    print(f"Policies: {len(policies)} | Sessions: {len(sessions)} | Responses: {response_count}")
    print(f"Deviations: {len(deviations)} | Status: {assessment.status}")
    print(f"URL: http://localhost:3000/assessments/{assessment.id}")
    print("=" * 60)


# ============================================================================
# Main Entry Point
# ============================================================================

def main(
    clean: bool = False,
    skip_interviews: bool = False,
    skip_scoring: bool = False,
) -> None:
    """Main seeding function."""
    print("\n" + "=" * 60)
    print("NVIDIA Inc Test Data Seeding Script")
    print("=" * 60)

    db = SessionLocal()

    try:
        if clean:
            clean_nvidia_data(db)

        # Get or create system user
        system_user = get_or_create_user(
            db,
            "system@nvidia-test.local",
            "System Administrator"
        )

        # 1. Load built-in frameworks
        frameworks = load_builtin_frameworks(db)

        # 2. Create NVIDIA custom framework
        nvidia_framework = create_nvidia_framework(db)

        # 3. Create assessment
        assessment = create_nvidia_assessment(db, system_user)

        # 4. Set framework scope
        set_assessment_scope(db, assessment, frameworks, nvidia_framework)

        # 5. Create policies
        policies = create_policies(db, assessment)

        # 6. Create mappings
        create_mappings(db, policies)

        # 8-9. Create interview sessions and responses
        sessions = []
        response_count = 0
        if not skip_interviews:
            sessions = create_interview_sessions(db, assessment)
            response_count = create_interview_responses(db, sessions)
        else:
            print("\n8-9. Skipping interview creation...")

        # 10-11. Calculate scores and detect deviations
        deviations = []
        if not skip_scoring:
            calculate_scores(db, assessment)
            deviations = detect_deviations(db, assessment)
        else:
            print("\n10-11. Skipping scoring and deviation detection...")

        # 12. Update status
        update_assessment_status(db, assessment)

        # Commit all changes
        db.commit()

        # Print summary
        print_summary(
            assessment,
            policies,
            sessions,
            response_count,
            deviations,
        )

    except Exception as e:
        db.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Seed Nvidia Inc test data for compliance assessment"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean existing Nvidia Inc data before seeding",
    )
    parser.add_argument(
        "--skip-interviews",
        action="store_true",
        help="Skip creating interview sessions and responses",
    )
    parser.add_argument(
        "--skip-scoring",
        action="store_true",
        help="Skip score calculation and deviation detection",
    )

    args = parser.parse_args()

    main(
        clean=args.clean,
        skip_interviews=args.skip_interviews,
        skip_scoring=args.skip_scoring,
    )
