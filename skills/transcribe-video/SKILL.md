---
name: transcribe-video
description: Transcribe a YouTube or Instagram video. Use when the user wants a raw transcript or verbatim text from a video, without summarization.
argument-hint: <video-url>
---

# Transcribe Video

The user wants a raw transcript of a video. Use the `transcribe_only` MCP tool from the video-summarizer server to download and transcribe the video.

## Arguments

The user provided: $ARGUMENTS

If no URL was provided, ask the user for a YouTube or Instagram Reel URL.

## Workflow

1. Call the `transcribe_only` tool with the provided URL
2. Return the full transcript to the user
3. Do NOT summarize or extract lessons unless the user asks

## Supported URLs

- `youtube.com/watch?v=...`
- `youtu.be/...`
- `instagram.com/reel/...`

## Notes

- The transcript is verbatim speech-to-text — it may lack punctuation or have minor errors
- Short videos (under 2 minutes) will complete in a few seconds
- Longer videos (10+ minutes) may take up to 60 seconds to transcribe
