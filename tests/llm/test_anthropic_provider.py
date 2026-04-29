"""Tests for app/llm/anthropic_provider.py."""

from unittest.mock import MagicMock, patch

from app.llm.anthropic_provider import AnthropicProvider


def test_complete_returns_text():
    mock_message = MagicMock()
    mock_message.content[0].text = "Summarised newsletter text."

    with patch("app.llm.anthropic_provider.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_message
        provider = AnthropicProvider(api_key="test-key", model="claude-haiku-test")
        result = provider.complete(system="sys", user="user content")

    assert result == "Summarised newsletter text."


def test_complete_passes_model_and_messages():
    mock_message = MagicMock()
    mock_message.content[0].text = "result"

    with patch("app.llm.anthropic_provider.anthropic.Anthropic") as mock_cls:
        mock_create = mock_cls.return_value.messages.create
        mock_create.return_value = mock_message
        provider = AnthropicProvider(api_key="test-key", model="my-model")
        provider.complete(system="system text", user="user text")

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "my-model"
    assert call_kwargs["system"] == "system text"
    assert call_kwargs["messages"] == [{"role": "user", "content": "user text"}]


def test_complete_passes_max_tokens():
    mock_message = MagicMock()
    mock_message.content[0].text = "result"

    with patch("app.llm.anthropic_provider.anthropic.Anthropic") as mock_cls:
        mock_create = mock_cls.return_value.messages.create
        mock_create.return_value = mock_message
        provider = AnthropicProvider(api_key="test-key", model="my-model", max_tokens=1024)
        provider.complete(system="sys", user="user")

    assert mock_create.call_args.kwargs["max_tokens"] == 1024


def test_complete_raises_on_empty_content():
    mock_message = MagicMock()
    mock_message.content = []

    with patch("app.llm.anthropic_provider.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_message
        provider = AnthropicProvider(api_key="test-key", model="model")

        try:
            provider.complete(system="sys", user="user")
            assert False, "Expected ValueError"
        except ValueError:
            pass
