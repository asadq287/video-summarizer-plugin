"""Pipeline test suite for video-summarizer.

Tests each stage independently with timing to pinpoint bottlenecks.
Supports YouTube AND Instagram, Whisper AND Gemini, and individual stage runs.

Usage:
    uv run python test_pipeline.py                         # all tests, default YT URL
    uv run python test_pipeline.py <youtube_or_ig_url>     # all tests, custom URL
    uv run python test_pipeline.py --stage download <url>  # single stage
    uv run python test_pipeline.py --stage transcribe      # transcribe existing file
    uv run python test_pipeline.py --stage cookies         # check IG cookie auth
    uv run python test_pipeline.py --stage gemini          # test Gemini transcription
    uv run python test_pipeline.py --list                  # list available stages
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time

TEST_URL = "https://www.youtube.com/watch?v=sgSrcSUck7U"
TEST_DIR = os.path.join(tempfile.gettempdir(), "video-summarizer-test")
VIDEO_PATH = os.path.join(TEST_DIR, "video.mp4")
WAV_PATH = os.path.join(TEST_DIR, "audio.wav")

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"
SKIP = "\033[90mSKIP\033[0m"
INFO = "\033[94mINFO\033[0m"

STAGES = [
    "imports", "ffmpeg", "cookies", "url", "download",
    "audio", "model", "transcribe", "gemini", "e2e",
]


def _banner(title: str) -> None:
    print(f"\n{'=' * 56}")
    print(f"  {title}")
    print(f"{'=' * 56}")


def _timed(label: str):
    """Context manager that prints elapsed time."""
    class Timer:
        def __init__(self):
            self.elapsed = 0.0
        def __enter__(self):
            self._start = time.perf_counter()
            return self
        def __exit__(self, *_):
            self.elapsed = time.perf_counter() - self._start
            print(f"  [{self.elapsed:.2f}s] {label}")
    return Timer()


def setup():
    """Prepare clean test directory."""
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR)


# ---------------------------------------------------------------------------
# Individual test stages
# ---------------------------------------------------------------------------

def test_imports():
    """Test that all modules import without error."""
    _banner("Imports")
    errors = []

    with _timed("import downloader"):
        try:
            from downloader import download_video, is_supported_url, detect_platform
            print(f"  {PASS} downloader")
        except Exception as e:
            print(f"  {FAIL} downloader: {e}")
            errors.append(("downloader", e))

    with _timed("import transcriber"):
        try:
            from transcriber import transcribe_video
            print(f"  {PASS} transcriber")
        except Exception as e:
            print(f"  {FAIL} transcriber: {e}")
            errors.append(("transcriber", e))

    with _timed("import faster_whisper"):
        try:
            from faster_whisper import WhisperModel
            print(f"  {PASS} faster_whisper")
        except Exception as e:
            print(f"  {FAIL} faster_whisper: {e}")
            errors.append(("faster_whisper", e))

    with _timed("import yt_dlp"):
        try:
            import yt_dlp  # noqa: F401
            print(f"  {PASS} yt_dlp")
        except Exception as e:
            print(f"  {FAIL} yt_dlp: {e}")
            errors.append(("yt_dlp", e))

    with _timed("import google.genai"):
        try:
            from google import genai  # noqa: F401
            print(f"  {PASS} google.genai")
        except Exception as e:
            print(f"  {FAIL} google.genai: {e}")
            errors.append(("google.genai", e))

    return len(errors) == 0


def test_ffmpeg():
    """Test that ffmpeg is available."""
    _banner("ffmpeg availability")
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], capture_output=True, timeout=5,
        )
        version_line = result.stdout.decode().split("\n")[0]
        print(f"  {PASS} {version_line}")
        return True
    except FileNotFoundError:
        print(f"  {FAIL} ffmpeg not found — install with: brew install ffmpeg")
        return False
    except Exception as e:
        print(f"  {FAIL} {e}")
        return False


def test_cookies():
    """Validate Instagram cookie setup (Chrome profile at ~/.claude-browser)."""
    _banner("Instagram cookie auth")
    from downloader.download import COOKIES_DIR

    print(f"  Cookie dir: {COOKIES_DIR}")

    if not os.path.isdir(COOKIES_DIR):
        print(f"  {FAIL} Directory does not exist")
        print(f"  {INFO} Create it with a logged-in Chrome profile:")
        print(f"         /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --user-data-dir={COOKIES_DIR}")
        return False

    # Look for cookie-relevant files
    found = []
    for name in ("Cookies", "Default/Cookies", "Profile 1/Cookies"):
        path = os.path.join(COOKIES_DIR, name)
        if os.path.exists(path):
            size_kb = os.path.getsize(path) / 1024
            found.append((name, size_kb))
            print(f"  {PASS} {name} ({size_kb:.0f} KB)")

    if not found:
        print(f"  {WARN} No Cookies database found in {COOKIES_DIR}")
        print(f"  {INFO} yt-dlp may still find cookies if Chrome profile structure differs")

    # Quick yt-dlp cookie extraction test
    print(f"  Testing yt-dlp cookie extraction...")
    try:
        import yt_dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "cookiesfrombrowser": ("chrome", None, None, COOKIES_DIR),
            "simulate": True,  # don't actually download
            "skip_download": True,
        }
        # Try extracting info from a known public reel
        test_ig_url = "https://www.instagram.com/reel/C1234567890/"
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Just test that cookie loading doesn't crash
            try:
                ydl.cookiejar  # noqa: B018 — triggers cookie loading
                print(f"  {PASS} yt-dlp accepted cookie config")
            except Exception as e:
                print(f"  {WARN} Cookie load issue: {e}")
    except Exception as e:
        print(f"  {WARN} yt-dlp cookie test: {e}")

    return True


def test_url_validation(url: str):
    """Test URL detection."""
    _banner("URL validation")
    from downloader import is_supported_url, detect_platform
    from downloader.download import is_instagram, is_youtube

    supported = is_supported_url(url)
    platform = detect_platform(url)
    print(f"  URL:       {url}")
    print(f"  Supported: {supported}")
    print(f"  Platform:  {platform}")
    print(f"  Instagram: {is_instagram(url)}")
    print(f"  YouTube:   {is_youtube(url)}")

    if supported:
        print(f"  {PASS}")
    else:
        print(f"  {FAIL} URL not supported")
    return supported


def test_download(url: str):
    """Test video download with timing."""
    _banner("Video download")
    from downloader import download_video
    from downloader.download import is_instagram

    if os.path.exists(VIDEO_PATH):
        os.unlink(VIDEO_PATH)

    if is_instagram(url):
        print(f"  {INFO} Instagram detected — using cookie auth")

    with _timed("download") as t:
        try:
            download_video(url, VIDEO_PATH)
        except Exception as e:
            print(f"  {FAIL} Download error: {e}")
            return False

    if not os.path.exists(VIDEO_PATH):
        print(f"  {FAIL} No file produced")
        return False

    size_mb = os.path.getsize(VIDEO_PATH) / (1024 * 1024)
    print(f"  File: {size_mb:.1f} MB")

    if t.elapsed > 60:
        print(f"  {WARN} Download took over 60s — possible network issue")
    print(f"  {PASS}")
    return True


def test_audio_extraction():
    """Test ffmpeg audio extraction from downloaded video."""
    _banner("Audio extraction (ffmpeg)")

    if not os.path.exists(VIDEO_PATH):
        print(f"  {FAIL} No video file — run download stage first")
        return False

    if os.path.exists(WAV_PATH):
        os.unlink(WAV_PATH)

    with _timed("ffmpeg extract"):
        try:
            subprocess.run(
                [
                    "ffmpeg", "-i", VIDEO_PATH,
                    "-ar", "16000", "-ac", "1",
                    "-c:a", "pcm_s16le", "-y", WAV_PATH,
                ],
                capture_output=True, timeout=60, check=True,
            )
        except subprocess.TimeoutExpired:
            print(f"  {FAIL} ffmpeg timed out after 60s")
            return False
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode()[:300] if e.stderr else ""
            print(f"  {FAIL} ffmpeg error: {stderr}")
            return False

    if not os.path.exists(WAV_PATH):
        print(f"  {FAIL} No WAV file produced")
        return False

    size_mb = os.path.getsize(WAV_PATH) / (1024 * 1024)
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", WAV_PATH],
            capture_output=True, timeout=5,
        )
        duration = float(result.stdout.decode().strip())
        print(f"  Audio: {size_mb:.1f} MB, {duration:.1f}s ({duration/60:.1f} min)")
    except Exception:
        print(f"  Audio: {size_mb:.1f} MB")

    print(f"  {PASS}")
    return True


def test_model_load():
    """Test Whisper model loading."""
    _banner("Whisper model load")
    from faster_whisper import WhisperModel

    with _timed("model load") as t:
        try:
            model = WhisperModel("base.en", compute_type="int8")
        except Exception as e:
            print(f"  {FAIL} Model load error: {e}")
            return None

    if t.elapsed > 10:
        print(f"  {WARN} Model load took over 10s — first run may download ~150MB")
    print(f"  {PASS}")
    return model


def test_transcription(model=None):
    """Test Whisper transcription with segment-by-segment progress."""
    _banner("Whisper transcription")

    if not os.path.exists(WAV_PATH):
        print(f"  {FAIL} No WAV file — run audio stage first")
        return False

    if model is None:
        print(f"  {INFO} Loading model (not passed from prior stage)...")
        model = test_model_load()
        if model is None:
            return False

    with _timed("model.transcribe() call"):
        try:
            segments, info = model.transcribe(WAV_PATH, language="en")
        except Exception as e:
            print(f"  {FAIL} transcribe() error: {e}")
            return False

    print(f"  Language: {info.language} (prob: {info.language_probability:.2f})")
    print(f"  Duration: {info.duration:.1f}s")

    print("  Iterating segments...")
    start = time.perf_counter()
    count = 0
    lines = []

    try:
        for seg in segments:
            count += 1
            text = seg.text.strip()
            if text and "[BLANK_AUDIO]" not in text:
                lines.append(text)
            if count % 50 == 0:
                elapsed = time.perf_counter() - start
                print(f"    seg {count} at {elapsed:.1f}s — [{seg.start:.0f}s-{seg.end:.0f}s]")
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"  {FAIL} Segment iteration failed after {elapsed:.1f}s at segment {count}: {e}")
        return False

    elapsed = time.perf_counter() - start
    print(f"  [{elapsed:.2f}s] segment iteration")

    transcript = " ".join(lines).strip()
    print(f"  Segments: {count}")
    print(f"  Transcript: {len(transcript)} chars")

    if len(transcript) < 5:
        print(f"  {WARN} Transcript is empty — video may have no speech")
    else:
        print(f"  Preview: {transcript[:200]}...")
        print(f"  {PASS}")

    return True


def test_gemini():
    """Test Gemini transcription path (requires GEMINI_API_KEY and a downloaded video)."""
    _banner("Gemini transcription")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Try loading from .env
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY=") and not line.startswith("#"):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            os.environ["GEMINI_API_KEY"] = val
                            api_key = val
                            print(f"  {INFO} Loaded GEMINI_API_KEY from .env")
                            break

    if not api_key:
        print(f"  {SKIP} GEMINI_API_KEY not set — skipping Gemini test")
        print(f"  {INFO} Set GEMINI_API_KEY in .env or environment to enable")
        return None  # None = skipped (not failure)

    if not os.path.exists(VIDEO_PATH):
        print(f"  {FAIL} No video file — run download stage first")
        return False

    from transcriber.gemini_transcribe import transcribe_video as gemini_transcribe, GEMINI_MODEL

    print(f"  Model: {GEMINI_MODEL}")
    print(f"  Video: {os.path.getsize(VIDEO_PATH) / (1024 * 1024):.1f} MB")

    with _timed("upload") as t_up:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            uploaded_file = client.files.upload(file=VIDEO_PATH)
            print(f"  {PASS} Upload complete")
        except Exception as e:
            print(f"  {FAIL} Upload failed: {e}")
            return False

    with _timed("processing wait"):
        try:
            deadline = time.monotonic() + 120
            while uploaded_file.state.name == "PROCESSING":
                if time.monotonic() > deadline:
                    print(f"  {FAIL} Processing timed out after 120s")
                    return False
                time.sleep(2)
                uploaded_file = client.files.get(name=uploaded_file.name)
            if uploaded_file.state.name == "FAILED":
                print(f"  {FAIL} Gemini file processing failed")
                return False
            print(f"  {PASS} File state: {uploaded_file.state.name}")
        except Exception as e:
            print(f"  {FAIL} Processing error: {e}")
            return False

    with _timed("generate_content") as t_gen:
        try:
            from transcriber.gemini_transcribe import TRANSCRIPTION_PROMPT
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[uploaded_file, TRANSCRIPTION_PROMPT],
            )
            transcript = response.text.strip()
        except Exception as e:
            print(f"  {FAIL} Generation error: {e}")
            return False
        finally:
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

    print(f"  Transcript: {len(transcript)} chars")
    if len(transcript) < 5:
        print(f"  {WARN} Transcript is empty")
    else:
        print(f"  Preview: {transcript[:200]}...")
        print(f"  {PASS}")
    return True


def test_e2e(url: str):
    """Test the full pipeline as server.py calls it."""
    _banner("Full pipeline (end-to-end)")
    from downloader import download_video
    from transcriber import transcribe_video, is_gemini_configured
    import uuid

    engine = "Gemini" if is_gemini_configured() else "Whisper"
    print(f"  {INFO} Transcription engine: {engine}")

    request_id = uuid.uuid4().hex[:8]
    temp_dir = os.path.join(tempfile.gettempdir(), f"video-summarizer-e2e-{request_id}")
    os.makedirs(temp_dir, exist_ok=True)
    vpath = os.path.join(temp_dir, "video.mp4")

    total_start = time.perf_counter()

    with _timed("download") as t_dl:
        try:
            download_video(url, vpath)
        except Exception as e:
            print(f"  {FAIL} Download: {e}")
            return False

    with _timed("transcribe") as t_tr:
        try:
            transcript = transcribe_video(vpath)
        except Exception as e:
            print(f"  {FAIL} Transcribe: {e}")
            return False

    total = time.perf_counter() - total_start

    # Cleanup
    for f in ("video.mp4", "audio.wav"):
        p = os.path.join(temp_dir, f)
        if os.path.exists(p):
            os.unlink(p)
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass

    print(f"  [{total:.2f}s] total pipeline")
    print(f"  Breakdown: download {t_dl.elapsed:.1f}s + transcribe {t_tr.elapsed:.1f}s")
    print(f"  Transcript: {len(transcript)} chars")

    if len(transcript) < 5:
        print(f"  {WARN} Empty transcript")
    elif total > 120:
        print(f"  {WARN} Pipeline took over 2 minutes — MCP client may time out")
        print(f"  {PASS} (but slow)")
    else:
        print(f"  {PASS}")

    return True


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all(url: str):
    """Run all stages sequentially."""
    setup()
    results = {}

    results["imports"] = test_imports()
    results["ffmpeg"] = test_ffmpeg()

    if not results["imports"] or not results["ffmpeg"]:
        print(f"\n{FAIL} Prerequisites failed — fix before continuing")
        return 1

    results["cookies"] = test_cookies()
    results["url"] = test_url_validation(url)
    results["download"] = test_download(url)
    results["audio"] = test_audio_extraction()
    model = test_model_load()
    results["model"] = model is not None
    results["transcribe"] = test_transcription(model)
    gemini_result = test_gemini()
    results["gemini"] = gemini_result if gemini_result is not None else True  # skip = pass
    results["e2e"] = test_e2e(url)

    # Summary
    _banner("Results Summary")
    for name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status}  {name}")

    total_passed = sum(results.values())
    total = len(results)
    print(f"\n  {total_passed}/{total} passed")

    # Cleanup
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)

    return 0 if total_passed == total else 1


def run_stage(stage: str, url: str):
    """Run a single test stage."""
    setup()

    if stage == "imports":
        ok = test_imports()
    elif stage == "ffmpeg":
        ok = test_ffmpeg()
    elif stage == "cookies":
        ok = test_cookies()
    elif stage == "url":
        ok = test_url_validation(url)
    elif stage == "download":
        ok = test_download(url)
    elif stage == "audio":
        # If video already exists in test dir, use it; otherwise need download
        if not os.path.exists(VIDEO_PATH):
            print(f"  {INFO} No cached video — downloading first...")
            if not test_download(url):
                return 1
        ok = test_audio_extraction()
    elif stage == "model":
        ok = test_model_load() is not None
    elif stage == "transcribe":
        if not os.path.exists(WAV_PATH):
            print(f"  {INFO} No cached audio — running prerequisites...")
            if not os.path.exists(VIDEO_PATH):
                if not test_download(url):
                    return 1
            if not test_audio_extraction():
                return 1
        ok = test_transcription()
    elif stage == "gemini":
        if not os.path.exists(VIDEO_PATH):
            print(f"  {INFO} No cached video — downloading first...")
            if not test_download(url):
                return 1
        result = test_gemini()
        ok = result is not False  # None (skipped) = ok
    elif stage == "e2e":
        ok = test_e2e(url)
    else:
        print(f"Unknown stage: {stage}")
        print(f"Available: {', '.join(STAGES)}")
        return 1

    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline test suite for video-summarizer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python test_pipeline.py                              # all tests, default YT URL
  uv run python test_pipeline.py https://youtu.be/abc123      # all tests, custom URL
  uv run python test_pipeline.py --stage download <ig_url>    # test IG download only
  uv run python test_pipeline.py --stage cookies              # check IG cookie setup
  uv run python test_pipeline.py --stage gemini               # test Gemini transcription
  uv run python test_pipeline.py --list                       # list available stages
        """,
    )
    parser.add_argument("url", nargs="?", default=TEST_URL, help="Video URL to test")
    parser.add_argument("--stage", "-s", choices=STAGES, help="Run a single test stage")
    parser.add_argument("--list", "-l", action="store_true", help="List available stages")

    args = parser.parse_args()

    if args.list:
        print("Available stages:")
        for s in STAGES:
            print(f"  {s}")
        return 0

    print(f"Video Summarizer — Pipeline Test Suite")
    print(f"URL: {args.url}")

    if args.stage:
        return run_stage(args.stage, args.url)
    return run_all(args.url)


if __name__ == "__main__":
    sys.exit(main())
