#!/usr/bin/env bash
# Bootstrap script for video-summarizer plugin.
# Ensures all writable paths exist, deps are installed, then starts the MCP server.
# Called by plugin.json instead of `uv run server.py` directly.

set -euo pipefail

# Co-Work doesn't inherit shell PATH — add common install locations
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"
CACHE_BASE="$HOME/.cache/claude-plugins/video-summarizer"

# Writable directories for uv, whisper models, and logs
export UV_PROJECT_ENVIRONMENT="$CACHE_BASE/.venv"
export UV_CACHE_DIR="$CACHE_BASE/cache"
export WHISPER_MODELS_DIR="$CACHE_BASE/models"
export VIDEO_SUMMARIZER_LOG_DIR="$CACHE_BASE/logs"
export PYTHONUNBUFFERED=1

# Create all writable directories
mkdir -p "$UV_PROJECT_ENVIRONMENT" "$UV_CACHE_DIR" "$WHISPER_MODELS_DIR" "$VIDEO_SUMMARIZER_LOG_DIR"

# Preflight checks
if ! command -v uv &>/dev/null; then
    echo "ERROR: uv not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    exit 1
fi

if ! command -v ffmpeg &>/dev/null; then
    echo "ERROR: ffmpeg not found. Install with: brew install ffmpeg" >&2
    exit 1
fi

# Install deps and run server (uv run does sync automatically)
exec uv run --project "$PLUGIN_DIR" "$PLUGIN_DIR/server.py"
