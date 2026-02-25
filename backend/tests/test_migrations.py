import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, inspect
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import (
    User,
    Role,
    CSFFunction,
    CSFCategory,
    CSFSubcategory,
    Assessment,
    Policy,
    PolicyMapping,
    AuditLog,
)


def test_migration_file_is_valid_python():
    """Test that the migration file is valid Python syntax."""
    migration_path = (
        Path(__file__).parent.parent / "alembic" / "versions" / "001_initial_schema.py"
    )
    assert migration_path.exists(), "Migration file does not exist"

    spec = importlib.util.spec_from_file_location("migration", migration_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert hasattr(module, "upgrade"), "Migration missing upgrade function"
    assert hasattr(module, "downgrade"), "Migration missing downgrade function"
    assert hasattr(module, "revision"), "Migration missing revision"


def test_all_models_create_tables():
    """Test that all SQLAlchemy models can create their tables."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = [
        "roles",
        "users",
        "user_roles",
        "csf_functions",
        "csf_categories",
        "csf_subcategories",
        "assessments",
        "policies",
        "policy_mappings",
        "audit_logs",
    ]

    for table in expected_tables:
        assert table in tables, f"Table {table} was not created"


def test_user_model_has_required_columns():
    """Test that the User model has all required columns."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("users")}

    required_columns = {"id", "email", "name", "is_active", "created_at", "updated_at"}
    assert required_columns.issubset(columns)


def test_audit_log_model_has_required_columns():
    """Test that the AuditLog model has all required columns."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("audit_logs")}

    required_columns = {
        "id",
        "user_id",
        "action",
        "entity_type",
        "entity_id",
        "timestamp",
    }
    assert required_columns.issubset(columns)


def test_role_model_has_required_columns():
    """Test that the Role model has all required columns."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    columns = {col["name"] for col in inspector.get_columns("roles")}

    required_columns = {"id", "name", "description", "created_at"}
    assert required_columns.issubset(columns)
