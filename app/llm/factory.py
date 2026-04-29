"""Factory: read DB config and return the configured LLMProvider."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import get_db_config, get_settings


def get_llm_provider(db: Session):
    """Read DB config, instantiate, and return the appropriate LLMProvider."""
    provider = get_db_config(db, "llm.provider")
    model = get_db_config(db, "llm.model")

    max_tokens = get_settings().llm_max_tokens

    if provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        api_key = get_settings().anthropic_api_key
        return AnthropicProvider(api_key=api_key, model=model, max_tokens=max_tokens)

    if provider == "openai":
        from app.llm.openai_provider import OpenAIProvider

        api_key = get_settings().openai_api_key
        base_url = get_db_config(db, "llm.openai_base_url")
        return OpenAIProvider(
            api_key=api_key, model=model, base_url=base_url, max_tokens=max_tokens
        )

    raise ValueError(f"Unknown LLM provider: {provider!r}")


def get_llm_user_prompt(db: Session) -> str:
    """Return the user's personalisation prompt from DB config."""
    return get_db_config(db, "llm.prompt")
