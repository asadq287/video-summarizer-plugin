"""Audio transcription module using faster-whisper.

Extracts audio from video via ffmpeg, then transcribes locally
using the faster-whisper CTranslate2 model.
"""

import os
import subprocess
import concurrent.futures
from faster_whisper import WhisperModel

# Lazy-loaded model singleton
_model: WhisperModel | None = None

TRANSCRIBE_TIMEOUT = 300  # 5 minutes max for transcription


def _get_model() -> WhisperModel:
    """Load the whisper model once and cache it."""
    global _model
    if _model is None:
        _model = WhisperModel("base.en", compute_type="int8")
    return _model


def _extract_audio(video_path: str, wav_path: str) -> None:
    """Extract audio from video as 16kHz mono WAV (whisper requirement)."""
    subprocess.run(
        [
            "ffmpeg",
            "-i", video_path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            "-y",
            wav_path,
        ],
        capture_output=True,
        timeout=60,
        check=True,
    )


def _run_transcription(wav_path: str) -> str:
    """Run whisper transcription in a thread."""
    model = _get_model()
    segments, _ = model.transcribe(wav_path, language="en")

    lines = []
    for segment in segments:
        text = segment.text.strip()
        if text and "[BLANK_AUDIO]" not in text:
            lines.append(text)

    return " ".join(lines).strip()


def transcribe_video(video_path: str) -> str:
    """Transcribe speech from a video file.

    Args:
        video_path: Path to the video file (MP4).

    Returns:
        The transcribed text as a single string.

    Raises:
        RuntimeError: If audio extraction or transcription fails.
    """
    wav_path = video_path.rsplit(".", 1)[0] + ".wav"

    try:
        _extract_audio(video_path, wav_path)

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run_transcription, wav_path)
            try:
                return future.result(timeout=TRANSCRIBE_TIMEOUT)
            except concurrent.futures.TimeoutError:
                raise RuntimeError(f"Transcription timed out after {TRANSCRIBE_TIMEOUT}s")

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode()[:500] if e.stderr else ""
        raise RuntimeError(f"Audio extraction failed: {stderr}") from e

    finally:
        if os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except OSError:
                pass
