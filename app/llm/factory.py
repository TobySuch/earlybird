"""Factory: read DB config and return the configured LLMProvider."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_db_config, get_settings


def _role_config(db: Session, role: str | None, key: str) -> str:
    """Read llm.{role}.{key}, falling back to the global llm.{key} when empty."""
    if role:
        value = get_db_config(db, f"llm.{role}.{key}")
        if value:
            return value
    return get_db_config(db, f"llm.{key}")


def get_llm_provider(db: Session, role: str | None = None):
    """Read DB config, instantiate, and return the appropriate LLMProvider.

    With a role (e.g. "reporter" or "editor"), llm.{role}.* config keys take
    precedence; empty role keys inherit the global llm.* values.
    """
    provider = _role_config(db, role, "provider")
    model = _role_config(db, role, "model")

    max_tokens = get_settings().llm_max_tokens

    if provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        api_key = get_settings().anthropic_api_key
        return AnthropicProvider(api_key=api_key, model=model, max_tokens=max_tokens)

    if provider == "openai":
        from app.llm.openai_provider import OpenAIProvider

        api_key = get_settings().openai_api_key
        base_url = _role_config(db, role, "openai_base_url")
        return OpenAIProvider(
            api_key=api_key, model=model, base_url=base_url, max_tokens=max_tokens
        )

    raise ValueError(f"Unknown LLM provider: {provider!r}")


def get_llm_user_prompt(db: Session) -> str:
    """Return the user's personalisation prompt from DB config."""
    return get_db_config(db, "llm.prompt")
