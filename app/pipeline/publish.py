"""Publishing: generate MP3 via TTS, upload to Audiobookshelf."""

from app.models import Episode


def run(db, episode: Episode) -> None:
    """Generate audio and upload to ABS.

    Steps:
    1. Send episode.podcast_script to OpenAI TTS (tts-1-hd) or ElevenLabs.
    2. Save MP3 to data/audio/episode_{episode.id}.mp3.
    3. Update episode.audio_path.
    4. If ABS is configured: upload via ABS API, store abs_episode_id.
    """
    # TODO: implement TTS + ABS upload
    raise NotImplementedError
