# Transcriber Module

Transcribes video audio to text using `faster-whisper` (CTranslate2-based local inference).

## Key Functions

- `transcribe_video(video_path)` — Extracts audio, transcribes speech, returns text string.

## Pipeline

1. **Extract audio:** `ffmpeg` converts video to 16kHz mono WAV (whisper requirement)
2. **Transcribe:** `faster-whisper` with `base.en` model (auto-downloads ~150MB on first use)
3. **Clean up:** Removes temp WAV file, filters out `[BLANK_AUDIO]` markers

## Model

- Model: `base.en` (English-only, fastest)
- Compute type: `int8` (CPU-optimized)
- Cached as singleton — loaded once per server lifetime
