# Downloader Module

Downloads videos from Instagram and YouTube using the `yt-dlp` Python API.

## Key Functions

- `download_video(url, output_path)` — Downloads video as MP4. Uses browser cookies from `~/.claude-browser` for Instagram authentication. YouTube works without cookies.
- `is_supported_url(url)` — Checks if URL is from instagram.com or youtube.com/youtu.be.
- `detect_platform(url)` — Returns "Instagram Reel" or "YouTube video".

## Platform Detection

- **Instagram:** `instagram.com` in URL → passes `cookiesfrombrowser` option to yt-dlp
- **YouTube:** `youtube.com` or `youtu.be` in URL → no cookies needed

## Validation

Downloaded files must be >50KB to be considered valid. Smaller files are deleted and treated as failures.
