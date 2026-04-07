"""Video transcription using Google Gemini's multimodal capabilities.

Uploads the video directly to Gemini and uses its multimodal model
to transcribe audio, bypassing ffmpeg and local Whisper inference.
"""

import os
import time

from google import genai

GEMINI_MODEL = "gemini-2.0-flash"

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

    client = genai.Client(api_key=api_key)
    uploaded_file = None

    try:
        uploaded_file = client.files.upload(file=video_path)

        # Wait for Gemini to finish processing the video
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(2)
            uploaded_file = client.files.get(name=uploaded_file.name)

        if uploaded_file.state.name == "FAILED":
            raise RuntimeError("Gemini failed to process the video file")

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[uploaded_file, TRANSCRIPTION_PROMPT],
        )

        return response.text.strip()

    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Gemini transcription failed: {e}") from e
    finally:
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass
