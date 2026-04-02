"""Tests for app/tts/elevenlabs_provider.py."""

from unittest.mock import MagicMock, patch

from app.tts.elevenlabs_provider import ElevenLabsProvider


def test_generate_writes_mp3(tmp_path):
    fake_audio = b"FAKEMP3DATA"
    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = iter([fake_audio])

    with patch("app.tts.elevenlabs_provider.ElevenLabs", return_value=mock_client):
        provider = ElevenLabsProvider(api_key="key")
        result = provider.generate(
            voice_id="v1",
            model_id="eleven_monolingual_v1",
            text="Hello world",
            episode_id=42,
            audio_dir=tmp_path,
        )

    assert result == tmp_path / "episode_42.mp3"
    assert result.read_bytes() == fake_audio


def test_generate_calls_elevenlabs_with_correct_args(tmp_path):
    mock_client = MagicMock()
    mock_client.text_to_speech.convert.return_value = iter([b"audio"])

    with patch("app.tts.elevenlabs_provider.ElevenLabs", return_value=mock_client):
        provider = ElevenLabsProvider(api_key="mykey")
        provider.generate(
            voice_id="myvoice",
            model_id="eleven_turbo_v2",
            text="Test text",
            episode_id=1,
            audio_dir=tmp_path,
        )

    mock_client.text_to_speech.convert.assert_called_once_with(
        voice_id="myvoice",
        text="Test text",
        model_id="eleven_turbo_v2",
        output_format="mp3_44100_128",
    )
