"""Tests for app/tts/openai_provider.py."""

from unittest.mock import MagicMock, patch

from app.tts.openai_provider import OpenAITTSProvider


def test_generate_writes_mp3(tmp_path):
    fake_audio = b"FAKEMP3DATA"
    mock_response = MagicMock()
    mock_response.iter_bytes.return_value = iter([fake_audio])

    with patch("app.tts.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value.audio.speech.create.return_value = mock_response
        provider = OpenAITTSProvider(api_key="test-key")
        result = provider.generate(
            voice_id="alloy",
            model_id="tts-1",
            text="Hello world",
            episode_id=42,
            audio_dir=tmp_path,
        )

    assert result == tmp_path / "episode_42.mp3"
    assert result.read_bytes() == fake_audio


def test_generate_passes_correct_args(tmp_path):
    mock_response = MagicMock()
    mock_response.iter_bytes.return_value = iter([b"audio"])

    with patch("app.tts.openai_provider.openai.OpenAI") as mock_cls:
        mock_create = mock_cls.return_value.audio.speech.create
        mock_create.return_value = mock_response
        provider = OpenAITTSProvider(api_key="key")
        provider.generate(
            voice_id="nova",
            model_id="tts-1-hd",
            text="Test input",
            episode_id=7,
            audio_dir=tmp_path,
        )

    mock_create.assert_called_once_with(
        model="tts-1-hd",
        voice="nova",
        input="Test input",
        response_format="mp3",
    )


def test_base_url_passed_to_client(tmp_path):
    mock_response = MagicMock()
    mock_response.iter_bytes.return_value = iter([b"audio"])

    with patch("app.tts.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value.audio.speech.create.return_value = mock_response
        OpenAITTSProvider(api_key="key", base_url="http://localhost:8080/v1")

    _, kwargs = mock_cls.call_args
    assert kwargs.get("base_url") == "http://localhost:8080/v1"


def test_empty_base_url_not_passed_to_client(tmp_path):
    mock_response = MagicMock()
    mock_response.iter_bytes.return_value = iter([b"audio"])

    with patch("app.tts.openai_provider.openai.OpenAI") as mock_cls:
        mock_cls.return_value.audio.speech.create.return_value = mock_response
        OpenAITTSProvider(api_key="key", base_url="")

    _, kwargs = mock_cls.call_args
    assert "base_url" not in kwargs
