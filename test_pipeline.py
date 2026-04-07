"""Pipeline test suite for video-summarizer.

Tests each stage independently with timing to pinpoint bottlenecks.
Run: uv run python test_pipeline.py [youtube_url]
"""

import os
import sys
import shutil
import tempfile
import time

TEST_URL = "https://www.youtube.com/watch?v=sgSrcSUck7U"
TEST_DIR = os.path.join(tempfile.gettempdir(), "video-summarizer-test")
VIDEO_PATH = os.path.join(TEST_DIR, "video.mp4")
WAV_PATH = os.path.join(TEST_DIR, "audio.wav")

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"


def _banner(title: str) -> None:
    print(f"\n{'=' * 50}")
    print(f"  {title}")
    print(f"{'=' * 50}")


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


def test_1_imports():
    """Test that all modules import without error."""
    _banner("Test 1: Imports")
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
            import yt_dlp
            print(f"  {PASS} yt_dlp")
        except Exception as e:
            print(f"  {FAIL} yt_dlp: {e}")
            errors.append(("yt_dlp", e))

    return len(errors) == 0


def test_2_ffmpeg():
    """Test that ffmpeg is available."""
    _banner("Test 2: ffmpeg availability")
    import subprocess
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, timeout=5,
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


def test_3_url_validation(url: str):
    """Test URL detection."""
    _banner("Test 3: URL validation")
    from downloader import is_supported_url, detect_platform

    supported = is_supported_url(url)
    platform = detect_platform(url)
    print(f"  URL: {url}")
    print(f"  Supported: {supported}")
    print(f"  Platform: {platform}")

    if supported:
        print(f"  {PASS}")
    else:
        print(f"  {FAIL} URL not supported")
    return supported


def test_4_download(url: str):
    """Test video download with timing."""
    _banner("Test 4: Video download")
    from downloader import download_video

    if os.path.exists(VIDEO_PATH):
        os.unlink(VIDEO_PATH)

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


def test_5_audio_extraction():
    """Test ffmpeg audio extraction from downloaded video."""
    _banner("Test 5: Audio extraction (ffmpeg)")
    import subprocess

    if not os.path.exists(VIDEO_PATH):
        print(f"  {FAIL} No video file — skipping (test 4 must pass first)")
        return False

    if os.path.exists(WAV_PATH):
        os.unlink(WAV_PATH)

    with _timed("ffmpeg extract") as t:
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
    # Get duration
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


def test_6_model_load():
    """Test Whisper model loading."""
    _banner("Test 6: Whisper model load")
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


def test_7_transcription(model):
    """Test transcription with segment-by-segment progress."""
    _banner("Test 7: Transcription")

    if model is None:
        print(f"  {FAIL} No model — skipping (test 6 must pass first)")
        return False

    if not os.path.exists(WAV_PATH):
        print(f"  {FAIL} No WAV file — skipping (test 5 must pass first)")
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
    text_len = 0
    lines = []

    try:
        for seg in segments:
            count += 1
            text = seg.text.strip()
            if text and "[BLANK_AUDIO]" not in text:
                lines.append(text)
                text_len += len(text)
            # Progress every 50 segments
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
        print(f"  Preview: {transcript[:150]}...")
        print(f"  {PASS}")

    return True


def test_8_full_pipeline(url: str):
    """Test the full pipeline as server.py calls it."""
    _banner("Test 8: Full pipeline (end-to-end)")
    from downloader import download_video
    from transcriber import transcribe_video
    import uuid

    request_id = uuid.uuid4().hex[:8]
    temp_dir = os.path.join(tempfile.gettempdir(), f"video-summarizer-e2e-{request_id}")
    os.makedirs(temp_dir, exist_ok=True)
    vpath = os.path.join(temp_dir, "video.mp4")

    total_start = time.perf_counter()

    with _timed("download"):
        try:
            download_video(url, vpath)
        except Exception as e:
            print(f"  {FAIL} Download: {e}")
            return False

    with _timed("transcribe") as t_trans:
        try:
            transcript = transcribe_video(vpath)
        except Exception as e:
            print(f"  {FAIL} Transcribe: {e}")
            return False

    total = time.perf_counter() - total_start
    print(f"  [{total:.2f}s] total pipeline")
    print(f"  Transcript: {len(transcript)} chars")

    # Cleanup
    for f in ("video.mp4", "audio.wav"):
        p = os.path.join(temp_dir, f)
        if os.path.exists(p):
            os.unlink(p)
    try:
        os.rmdir(temp_dir)
    except OSError:
        pass

    if len(transcript) < 5:
        print(f"  {WARN} Empty transcript")
    elif total > 120:
        print(f"  {WARN} Pipeline took over 2 minutes")
    else:
        print(f"  {PASS}")

    return True


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else TEST_URL
    print(f"Video Summarizer — Pipeline Test Suite")
    print(f"URL: {url}")

    setup()
    results = {}

    results["imports"] = test_1_imports()
    results["ffmpeg"] = test_2_ffmpeg()

    if not results["imports"] or not results["ffmpeg"]:
        print(f"\n{FAIL} Prerequisites failed — fix before continuing")
        return 1

    results["url"] = test_3_url_validation(url)
    results["download"] = test_4_download(url)
    results["audio"] = test_5_audio_extraction()
    model = test_6_model_load()
    results["model"] = model is not None
    results["transcription"] = test_7_transcription(model)
    results["e2e"] = test_8_full_pipeline(url)

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


if __name__ == "__main__":
    sys.exit(main())
