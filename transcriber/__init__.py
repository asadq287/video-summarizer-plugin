import os


def transcribe_video(video_path: str) -> str:
    """Transcribe speech from a video file.

    Uses Gemini if GEMINI_API_KEY is set, otherwise falls back to
    local faster-whisper transcription.
    """
    if os.environ.get("GEMINI_API_KEY"):
        from .gemini_transcribe import transcribe_video as _gemini
        return _gemini(video_path)
    from .transcribe import transcribe_video as _whisper
    return _whisper(video_path)


def is_gemini_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))
