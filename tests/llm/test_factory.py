"""Tests for app/llm/factory.py role-based provider resolution."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import set_db_config
from app.database import Base
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.factory import get_llm_provider
from app.llm.openai_provider import OpenAIProvider


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_default_provider_is_anthropic_with_global_model(db):
    provider = get_llm_provider(db)
    assert isinstance(provider, AnthropicProvider)
    assert provider._model == "claude-haiku-4-5-20251001"


def test_role_inherits_globals_when_role_keys_empty(db):
    set_db_config(db, "llm.model", "global-model")
    provider = get_llm_provider(db, role="reporter")
    assert isinstance(provider, AnthropicProvider)
    assert provider._model == "global-model"


def test_role_model_overrides_global(db):
    set_db_config(db, "llm.model", "global-model")
    set_db_config(db, "llm.reporter.model", "cheap-model")
    provider = get_llm_provider(db, role="reporter")
    assert provider._model == "cheap-model"


def test_role_provider_overrides_global(db):
    set_db_config(db, "llm.provider", "anthropic")
    set_db_config(db, "llm.reporter.provider", "openai")
    set_db_config(db, "llm.reporter.model", "local-model")
    provider = get_llm_provider(db, role="reporter")
    assert isinstance(provider, OpenAIProvider)
    assert provider._model == "local-model"


def test_role_base_url_overrides_global(db):
    set_db_config(db, "llm.provider", "openai")
    set_db_config(db, "llm.openai_base_url", "https://global.example")
    set_db_config(db, "llm.reporter.openai_base_url", "http://localhost:11434/v1")
    provider = get_llm_provider(db, role="reporter")
    assert str(provider._client.base_url) == "http://localhost:11434/v1/"


def test_role_base_url_inherits_global_when_empty(db):
    set_db_config(db, "llm.provider", "openai")
    set_db_config(db, "llm.openai_base_url", "https://global.example")
    provider = get_llm_provider(db, role="editor")
    assert str(provider._client.base_url).rstrip("/") == "https://global.example"


def test_roles_resolve_independently(db):
    set_db_config(db, "llm.reporter.model", "cheap-model")
    set_db_config(db, "llm.editor.model", "smart-model")
    assert get_llm_provider(db, role="reporter")._model == "cheap-model"
    assert get_llm_provider(db, role="editor")._model == "smart-model"


def test_unknown_provider_raises(db):
    set_db_config(db, "llm.provider", "wat")
    with pytest.raises(ValueError):
        get_llm_provider(db)
