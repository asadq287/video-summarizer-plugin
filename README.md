# Video Summarizer — Claude Plugin

A Claude Co-Work plugin that downloads and transcribes YouTube videos and Instagram Reels, then extracts key lessons and actionable steps.

## Features

- Transcribe YouTube videos and Instagram Reels
- Extract key lessons with actionable steps
- Local transcription via Whisper (default) or cloud via Gemini Flash
- Works as a full Claude Co-Work plugin with skills and MCP tools

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [ffmpeg](https://ffmpeg.org/) — `brew install ffmpeg`
- For Instagram: a logged-in Chrome profile at `~/.claude-browser`

## Installation

### As a Claude Co-Work Plugin (Marketplace)

1. Open Claude Co-Work
2. Go to **Plugins > Personal Plugins > Add Marketplace**
3. Paste: `Core-Business-Flow/Video-transcription-and-summariser-plugin`
4. Install the **video-summarizer** plugin

### Manual (Claude Code)

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "video-summarizer": {
      "command": "uv",
      "args": ["run", "server.py"],
      "cwd": "/path/to/this/repo"
    }
  }
}
```

Then run `uv sync` in the repo directory.

## Usage

### Skills (Claude Co-Work)

- `/video-summarizer:summarize-video <url>` — Transcribe and extract key lessons
- `/video-summarizer:transcribe-video <url>` — Get raw transcript only

### MCP Tools (Claude Code)

- `summarize_video(url)` — Download, transcribe, and return transcript with summarization prompt
- `transcribe_only(url)` — Download and transcribe, returning raw text

### Supported URLs

- `youtube.com/watch?v=...`
- `youtu.be/...`
- `instagram.com/reel/...`

## Configuration

### Gemini API Key (Optional)

For cloud-based transcription instead of local Whisper, set a Gemini API key:

1. Get a key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Create a `.env` file in the repo root:
   ```
   GEMINI_API_KEY=your_key_here
   ```

When installed as a plugin, you'll be prompted for the key during setup.

## Architecture

```
.claude-plugin/     ← Plugin manifest and marketplace config
skills/             ← Skill definitions for Claude Co-Work
server.py           ← FastMCP entry point, tool definitions
downloader/         ← yt-dlp Python API for IG + YouTube downloads
transcriber/        ← Whisper (local) and Gemini (cloud) transcription
logger.py           ← Structured file logging for diagnostics
```
