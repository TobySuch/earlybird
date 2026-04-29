"""Tests for app/llm/openai_provider.py."""

from unittest.mock import MagicMock, patch

from app.llm.openai_provider import OpenAIProvider


def test_complete_returns_text():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Summarised newsletter text."

    with patch("app.llm.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = mock_response
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        result = provider.complete(system="sys", user="user content")

    assert result == "Summarised newsletter text."


def test_complete_passes_model_and_messages():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "result"

    with patch("app.llm.openai_provider.openai.OpenAI") as mock_cls:
        mock_create = mock_cls.return_value.chat.completions.create
        mock_create.return_value = mock_response
        provider = OpenAIProvider(api_key="test-key", model="my-model")
        provider.complete(system="system text", user="user text")

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "my-model"
    assert {"role": "system", "content": "system text"} in call_kwargs["messages"]
    assert {"role": "user", "content": "user text"} in call_kwargs["messages"]


def test_complete_passes_max_tokens():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "result"

    with patch("app.llm.openai_provider.openai.OpenAI") as mock_cls:
        mock_create = mock_cls.return_value.chat.completions.create
        mock_create.return_value = mock_response
        provider = OpenAIProvider(api_key="test-key", model="my-model", max_tokens=512)
        provider.complete(system="sys", user="user")

    assert mock_create.call_args.kwargs["max_tokens"] == 512


def test_complete_raises_on_empty_content():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = ""

    with patch("app.llm.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = mock_response
        provider = OpenAIProvider(api_key="test-key", model="model")

        try:
            provider.complete(system="sys", user="user")
            assert False, "Expected ValueError"
        except ValueError:
            pass


def test_base_url_passed_to_client():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "ok"

    with patch("app.llm.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = mock_response
        OpenAIProvider(api_key="test-key", model="llama3", base_url="http://localhost:11434/v1")

    _, kwargs = mock_cls.call_args
    assert kwargs.get("base_url") == "http://localhost:11434/v1"


def test_empty_base_url_not_passed_to_client():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "ok"

    with patch("app.llm.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value.chat.completions.create.return_value = mock_response
        OpenAIProvider(api_key="test-key", model="gpt-4o", base_url="")

    _, kwargs = mock_cls.call_args
    assert "base_url" not in kwargs
