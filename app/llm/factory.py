"""Factory: read DB config and return the configured LLMProvider."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_db_config, get_settings

LLM_PROVIDER_KEY = "llm.provider"
LLM_MODEL_KEY = "llm.model"
LLM_PROMPT_KEY = "llm.prompt"

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_USER_PROMPT = ""


def get_llm_provider(db: Session):
    """Read DB config, instantiate, and return the appropriate LLMProvider."""
    provider = get_db_config(db, LLM_PROVIDER_KEY, DEFAULT_PROVIDER)
    model = get_db_config(db, LLM_MODEL_KEY, DEFAULT_MODEL)

    if provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        api_key = get_settings().anthropic_api_key
        return AnthropicProvider(api_key=api_key, model=model)

    raise ValueError(f"Unknown LLM provider: {provider!r}")


def get_llm_user_prompt(db: Session) -> str:
    """Return the user's personalisation prompt from DB config."""
    return get_db_config(db, LLM_PROMPT_KEY, DEFAULT_USER_PROMPT)
