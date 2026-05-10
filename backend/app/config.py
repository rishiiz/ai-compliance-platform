"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings

# Load .env from backend root (parent of app/) so it's found regardless of cwd
_backend_root = Path(__file__).resolve().parent.parent
_env_file = _backend_root / ".env"
load_dotenv(_env_file)


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = ConfigDict(
        env_file=_env_file if _env_file.exists() else None,
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    PROJECT_NAME: str = "AI Compliance Platform"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Required: validated at startup
    DATABASE_URL: str

    # Optional: if set, used for RAG embeddings. If not set and USE_LOCAL_EMBEDDINGS=true, local embeddings are used (no OpenAI).
    OPENAI_API_KEY: str = ""

    # When True (default), RAG uses local sentence-transformers for embeddings so OpenAI is not required. Set False to use OpenAI embeddings.
    USE_LOCAL_EMBEDDINGS: bool = True

    # Groq (LLM completion: Ask policy, rule extraction, explanations). When set, uses Groq + Llama 3.3 70B instead of OpenAI for chat.
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # RAG (Retrieval-Augmented Generation). Embeddings: local (sentence-transformers) when USE_LOCAL_EMBEDDINGS=true, else OpenAI.
    # RAG_STORAGE_BACKEND: "chroma" (default, on-disk) or "mysql" (store chunks+embeddings in app database).
    RAG_STORAGE_BACKEND: str = "chroma"
    RAG_CHROMA_PATH: str = ""
    RAG_ENABLED: bool = True
    RAG_MAX_CHUNKS_PER_POLICY: int = 200
    RAG_CHUNK_TOKENS: int = 512
    RAG_CHUNK_OVERLAP_TOKENS: int = 50
    RAG_TOP_K: int = 5
    RAG_TOP_K_MAX: int = 10
    RAG_TOP_K_MIN: int = 3
    RAG_HIGH_SIMILARITY_THRESHOLD: float = 0.85
    RAG_MIN_SIMILARITY: float = 0.75
    RAG_USE_RERANKER: bool = False
    RAG_RERANK_TOP_N: int = 5
    RAG_ASK_MAX_QUERY_LENGTH: int = 500
    RAG_ASK_MAX_CONTEXT_TOKENS: int = 4096
    RAG_ASK_MAX_TOKENS: int = 500
    RAG_ASK_TEMPERATURE: float = 0.2
    RAG_ASK_RATE_LIMIT_PER_HOUR: int = 60
    RAG_LONG_POLICY_CHARS: int = 8000  # use RAG path in rule extraction above this
    RAG_SEMANTIC_COMPRESSION: bool = True
    RAG_NORMALIZE_RULES_TO_KV: bool = False

    # RAG cache (Redis if REDIS_URL set, else in-memory)
    RAG_CACHE_TTL_SECONDS: int = 3600
    RAG_CACHE_RESPONSE: bool = True
    RAG_CACHE_CHUNKS: bool = True
    RAG_CACHE_EMBEDDINGS: bool = True
    RAG_CACHE_MAX_RESPONSES: int = 500
    RAG_CACHE_MAX_CHUNKS: int = 200
    RAG_CACHE_MAX_EMBEDDINGS: int = 1000
    REDIS_URL: str = ""

    # RAG metrics
    RAG_METRICS_ENABLED: bool = True
    RAG_METRICS_BUFFER_SIZE: int = 100

    # Optional: pre-generated section summaries for large policies
    RAG_USE_SUMMARIES: bool = False
    RAG_SUMMARY_MIN_CHARS: int = 15000

    # Company DB for Ask policy: when True, user questions are answered from policy content
    # searched in the company (external) database, then sent to Groq.
    USE_COMPANY_DB_FOR_ASK: bool = True
    COMPANY_POLICY_TABLE: str = "policy_documents"
    COMPANY_POLICY_CONTENT_COLUMN: str = "content"
    COMPANY_POLICY_TITLE_COLUMN: str = ""  # optional; if set, included in context
    COMPANY_POLICY_SEARCH_LIMIT: int = 10

    # File storage: Supabase (optional) or app database (MongoDB). When Supabase not set, files stored in policy_file_storage collection.
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "policy-files"

    # ZIP policy upload
    ZIP_UPLOAD_MAX_FILE_SIZE_MB: int = 50

    # API
    API_V1_PREFIX: str = "/api/v1"

    @field_validator("DATABASE_URL")
    @classmethod
    def required_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be set and non-empty")
        return v.strip()

    @field_validator("OPENAI_API_KEY", "GROQ_API_KEY", mode="before")
    @classmethod
    def strip_key(cls, v: object) -> str:
        if v is None:
            return ""
        return str(v).strip() if v else ""


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()


settings = get_settings()
