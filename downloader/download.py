"""Video downloader module using yt-dlp Python API.

Handles both Instagram Reels (with browser cookies) and YouTube videos.
"""

import os
import concurrent.futures
import yt_dlp

from logger import log, timer_start, timer_end


COOKIES_DIR = os.path.join(os.environ.get("HOME", ""), ".claude-browser")
MIN_VIDEO_SIZE = 50_000  # 50KB minimum for a valid video
DOWNLOAD_TIMEOUT = 120  # seconds — abort if download takes longer


def is_instagram(url: str) -> bool:
    return "instagram.com" in url


def is_youtube(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


def is_supported_url(url: str) -> bool:
    return is_instagram(url) or is_youtube(url)


def detect_platform(url: str) -> str:
    if is_instagram(url):
        return "Instagram Reel"
    if is_youtube(url):
        return "YouTube video"
    return "Unknown"


def _do_download(url: str, output_path: str, ydl_opts: dict) -> None:
    """Run yt-dlp download in a thread."""
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_video(url: str, output_path: str) -> str:
    """Download a video from Instagram or YouTube.

    Args:
        url: The video URL.
        output_path: Path where the MP4 file should be saved.

    Returns:
        The path to the downloaded video file.

    Raises:
        ValueError: If the URL is not supported.
        RuntimeError: If download fails or file is too small.
    """
    if not is_supported_url(url):
        raise ValueError(f"Unsupported URL. Must be from instagram.com or youtube.com/youtu.be: {url}")

    platform = "instagram" if is_instagram(url) else "youtube"
    log("download", f"Preparing {platform} download", url=url)

    ydl_opts = {
        "outtmpl": output_path,
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
    }

    # Instagram requires browser cookies for authentication
    if is_instagram(url):
        log("download", "Loading Instagram cookies", cookie_dir=COOKIES_DIR)
        ydl_opts["cookiesfrombrowser"] = ("chrome", None, None, COOKIES_DIR)

    timer_start("yt-dlp")
    log("download", "yt-dlp starting")
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_do_download, url, output_path, ydl_opts)
        try:
            future.result(timeout=DOWNLOAD_TIMEOUT)
        except concurrent.futures.TimeoutError:
            elapsed = timer_end("yt-dlp")
            log("download", "TIMED OUT", elapsed=f"{elapsed:.1f}s")
            raise RuntimeError(f"Download timed out after {DOWNLOAD_TIMEOUT}s")
    elapsed = timer_end("yt-dlp")
    log("download", "yt-dlp finished", elapsed=f"{elapsed:.1f}s")

    if not os.path.exists(output_path):
        log("download", "FAIL: no file produced")
        raise RuntimeError("Download completed but no file was produced")

    size = os.path.getsize(output_path)
    if size < MIN_VIDEO_SIZE:
        log("download", "FAIL: file too small", size=size)
        os.unlink(output_path)
        raise RuntimeError("Downloaded file is too small — likely corrupted or empty")

    log("download", "Download OK", size=f"{size / (1024*1024):.1f}MB", path=output_path)
    return output_path
