"""Video Summarizer MCP Server.

Downloads and transcribes Instagram Reels & YouTube videos,
returning the transcript for Claude to extract key lessons
and actionable steps.
"""

import os
import pathlib
import tempfile
import uuid
import concurrent.futures

# Load .env from the project root before anything reads env vars
_env_path = pathlib.Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and value:
            os.environ.setdefault(key, value)

from mcp.server.fastmcp import FastMCP

from downloader import download_video, is_supported_url, detect_platform
from transcriber import transcribe_video, is_gemini_configured

mcp = FastMCP("video-summarizer")

TOOL_TIMEOUT = 480  # 8 minutes max for entire tool execution

_gemini_hint_shown = False


def _transcription_engine() -> str:
    return "Gemini Flash" if is_gemini_configured() else "Whisper (local)"


def _maybe_gemini_hint() -> str:
    global _gemini_hint_shown
    if _gemini_hint_shown or is_gemini_configured():
        return ""
    _gemini_hint_shown = True
    return (
        "\n\n---\n\n"
        "**Tip:** For faster cloud-based transcription, you can set a `GEMINI_API_KEY` "
        "in the `env` block of your MCP server config (`.mcp.json`). This uses Gemini "
        "Flash to transcribe videos instead of local Whisper."
    )


def _run_pipeline(url: str, video_path: str) -> str:
    """Download and transcribe — runs in a thread with timeout."""
    download_video(url, video_path)
    return transcribe_video(video_path)


@mcp.tool()
def summarize_video(url: str) -> str:
    """Download and transcribe an Instagram Reel or YouTube video.

    Returns the full transcript with metadata. You (Claude) should then
    extract the key lessons from the video as succinctly as possible,
    and provide clear, actionable steps on how to carry out each lesson.

    Supports: instagram.com/reel/... and youtube.com / youtu.be URLs.
    """
    if not url or not isinstance(url, str):
        return "Error: A valid URL is required."

    if not is_supported_url(url):
        return "Error: URL must be from instagram.com or youtube.com/youtu.be."

    platform = detect_platform(url)
    request_id = uuid.uuid4().hex[:8]
    temp_dir = os.path.join(tempfile.gettempdir(), f"video-summarizer-{request_id}")
    os.makedirs(temp_dir, exist_ok=True)
    video_path = os.path.join(temp_dir, "video.mp4")

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run_pipeline, url, video_path)
            try:
                transcript = future.result(timeout=TOOL_TIMEOUT)
            except concurrent.futures.TimeoutError:
                return f"Error processing {platform}: timed out after {TOOL_TIMEOUT}s"

        if len(transcript) < 5:
            return (
                f"Transcription completed but no speech was detected in this {platform}. "
                "The video may be music-only or contain no spoken content."
            )

        return "\n".join([
            f"**Source:** {platform}",
            f"**URL:** {url}",
            f"**Transcription engine:** {_transcription_engine()}",
            f"**Transcript length:** {len(transcript)} characters",
            "",
            "---",
            "",
            "**Transcript:**",
            "",
            transcript,
            "",
            "---",
            "",
            "Please extract the **key lessons** from this transcript as succinctly as possible. "
            "For each lesson, provide **clear, actionable steps** on how to carry it out.",
        ]) + _maybe_gemini_hint()

    except Exception as e:
        return f"Error processing {platform}: {e}"

    finally:
        for filename in ("video.mp4", "audio.wav"):
            path = os.path.join(temp_dir, filename)
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass


@mcp.tool()
def transcribe_only(url: str) -> str:
    """Download and transcribe an Instagram Reel or YouTube video.

    Returns the raw transcript text without summarization instructions.
    Use this when you just need the spoken content from a video.

    Supports: instagram.com/reel/... and youtube.com / youtu.be URLs.
    """
    if not url or not isinstance(url, str):
        return "Error: A valid URL is required."

    if not is_supported_url(url):
        return "Error: URL must be from instagram.com or youtube.com/youtu.be."

    platform = detect_platform(url)
    request_id = uuid.uuid4().hex[:8]
    temp_dir = os.path.join(tempfile.gettempdir(), f"video-summarizer-{request_id}")
    os.makedirs(temp_dir, exist_ok=True)
    video_path = os.path.join(temp_dir, "video.mp4")

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run_pipeline, url, video_path)
            try:
                transcript = future.result(timeout=TOOL_TIMEOUT)
            except concurrent.futures.TimeoutError:
                return f"Error processing {platform}: timed out after {TOOL_TIMEOUT}s"

        if len(transcript) < 5:
            return (
                f"No speech detected in this {platform}. "
                "The video may be music-only or contain no spoken content."
            )

        return transcript + _maybe_gemini_hint()

    except Exception as e:
        return f"Error processing {platform}: {e}"

    finally:
        for filename in ("video.mp4", "audio.wav"):
            path = os.path.join(temp_dir, filename)
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except OSError:
                    pass
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass


if __name__ == "__main__":
    mcp.run()
