from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    app_name: str = "Compliance AI"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql://compliance:compliance@localhost:5432/compliance_ai"

    # OpenAI (for chat completions and embeddings)
    openai_api_key: str | None = None
    ai_model: str = "gpt-4o"
    ai_max_tokens: int = 4096
    ai_temperature: float = 0.3
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # Clustering
    similarity_threshold: float = 0.85
    clustering_min_cluster_size: int = 2

    # File uploads
    max_upload_size_mb: int = 10
    allowed_control_extensions: list[str] = [".csv", ".xlsx", ".xls"]
    allowed_policy_extensions: list[str] = [".pdf", ".docx", ".doc", ".txt", ".md"]

    # Scoring
    default_confidence_threshold: float = 0.5
    mapping_relevance_threshold: float = 70.0  # minimum relevance_percentage to store a mapping

    # LLM Scoring
    scoring_model: str = "gpt-4o-mini"
    scoring_model_enhanced: str = "gpt-4o"
    scoring_max_output_tokens: int = 1200

    # Chunking (for semantic relevance scoring)
    chunk_size_chars: int = 1200      # ~300 tokens (4 chars/token approx)
    chunk_overlap_chars: int = 150    # ~12% overlap
    chunk_min_sections: int = 2       # minimum detected headings to use semantic chunking mode

    # Aggregation (for semantic relevance scoring)
    mapping_top_k: int = 5           # mean of top-K chunk similarities per (policy, requirement) pair

    # JWT Authentication
    jwt_secret_key: str = "change-me-in-production-use-a-secure-random-key"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480
    jwt_refresh_token_expire_days: int = 7


settings = Settings()
