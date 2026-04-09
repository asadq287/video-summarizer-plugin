"""Video transcription using Google Gemini's multimodal capabilities.

Uploads the video directly to Gemini and uses its multimodal model
to transcribe audio, bypassing ffmpeg and local Whisper inference.
"""

import os
import time

from google import genai

from logger import log, timer_start, timer_end

GEMINI_MODEL = "gemini-2.5-flash"

TRANSCRIPTION_PROMPT = (
    "Transcribe all spoken words in this video verbatim. "
    "Return only the transcript text with no timestamps, "
    "speaker labels, or commentary."
)


def transcribe_video(video_path: str) -> str:
    """Transcribe speech from a video file using Gemini.

    Uploads the video to Gemini's File API, then uses the multimodal
    model to transcribe all spoken content.

    Args:
        video_path: Path to the video file (MP4).

    Returns:
        The transcribed text as a single string.

    Raises:
        RuntimeError: If the Gemini API call fails.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    log("gemini", "Starting Gemini transcription", model=GEMINI_MODEL, video=video_path)
    client = genai.Client(api_key=api_key)
    uploaded_file = None

    try:
        timer_start("gemini-upload")
        log("gemini", "Uploading video to Files API")
        uploaded_file = client.files.upload(file=video_path)
        upload_time = timer_end("gemini-upload")
        log("gemini", "Upload complete", elapsed=f"{upload_time:.1f}s")

        # Wait for Gemini to finish processing the video (max 120s)
        timer_start("gemini-process")
        log("gemini", "Waiting for processing", state=uploaded_file.state.name)
        deadline = time.monotonic() + 120
        poll_count = 0
        while uploaded_file.state.name == "PROCESSING":
            if time.monotonic() > deadline:
                elapsed = timer_end("gemini-process")
                log("gemini", "Processing TIMED OUT", elapsed=f"{elapsed:.1f}s", polls=poll_count)
                raise RuntimeError("Gemini file processing timed out after 120s")
            time.sleep(2)
            poll_count += 1
            uploaded_file = client.files.get(name=uploaded_file.name)
        process_time = timer_end("gemini-process")
        log("gemini", "Processing done", elapsed=f"{process_time:.1f}s", state=uploaded_file.state.name, polls=poll_count)

        if uploaded_file.state.name == "FAILED":
            log("gemini", "Processing FAILED")
            raise RuntimeError("Gemini failed to process the video file")

        timer_start("gemini-generate")
        log("gemini", "Calling generate_content")
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[uploaded_file, TRANSCRIPTION_PROMPT],
        )
        gen_time = timer_end("gemini-generate")

        transcript = response.text.strip()
        log("gemini", "Generation complete", elapsed=f"{gen_time:.1f}s", chars=len(transcript))
        return transcript

    except RuntimeError:
        raise
    except Exception as e:
        log("gemini", "EXCEPTION", error=str(e))
        raise RuntimeError(f"Gemini transcription failed: {e}") from e
    finally:
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
