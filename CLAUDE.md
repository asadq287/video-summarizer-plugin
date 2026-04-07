# Video Summarizer — Claude Plugin

MCP server that downloads and transcribes Instagram Reels & YouTube videos, returning transcripts for Claude to extract key lessons and actionable steps.

## Setup

```bash
uv sync        # install dependencies
uv run server.py  # start MCP server (stdio)
```

**System requirement:** `ffmpeg` must be installed (`brew install ffmpeg`).

**For Instagram:** Requires a logged-in Chrome profile at `~/.claude-browser` for cookie-based authentication.

## Tools

- `summarize_video(url)` — Download, transcribe, and prompt Claude to extract lessons + steps
- `transcribe_only(url)` — Download and transcribe, returning raw transcript

## Architecture

```
server.py          ← FastMCP entry point, tool definitions
downloader/        ← yt-dlp Python API for IG + YouTube downloads
transcriber/       ← faster-whisper local transcription
```

## Supported URLs

- `instagram.com/reel/...` (requires browser cookies)
- `youtube.com/watch?v=...`
- `youtu.be/...`
