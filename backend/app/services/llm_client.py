"""LLM client for chat completion. Groq-only: uses Groq + Llama 3.3 70B when GROQ_API_KEY is set; optional OpenAI fallback when Groq not set."""

from openai import OpenAI

from app.config import settings

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"


def get_completion_client() -> OpenAI:
    """Return an OpenAI-compatible client for chat completion. Uses Groq when GROQ_API_KEY is set."""
    groq_key = (getattr(settings, "GROQ_API_KEY", None) or "").strip()
    if groq_key:
        return OpenAI(
            api_key=groq_key,
            base_url=GROQ_BASE_URL,
        )
    return OpenAI(api_key=settings.OPENAI_API_KEY or "")


def get_completion_model() -> str:
    """Return the model id to use for chat completion (Groq Llama 3.3 70B or OpenAI gpt-4o-mini)."""
    groq_key = (getattr(settings, "GROQ_API_KEY", None) or "").strip()
    if groq_key:
        return getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile") or "llama-3.3-70b-versatile"
    return OPENAI_DEFAULT_MODEL


def is_groq_used() -> bool:
    """True if completion uses Groq (GROQ_API_KEY set)."""
    return bool((getattr(settings, "GROQ_API_KEY", None) or "").strip())


def is_completion_available() -> bool:
    """True if we have at least one LLM for completion (Groq or OpenAI with non-placeholder key)."""
    if is_groq_used():
        return True
    key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    return bool(key) and "your_openai_key_here" not in key.lower()
