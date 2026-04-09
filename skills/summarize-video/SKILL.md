---
name: summarize-video
description: Summarize a YouTube or Instagram video. Use when the user shares a video URL and wants key lessons, takeaways, or a summary extracted from it.
argument-hint: <video-url>
---

# Summarize Video

The user wants to summarize a video. Use the `summarize_video` MCP tool from the video-summarizer server to download and transcribe the video, then extract key lessons.

## Arguments

The user provided: $ARGUMENTS

If no URL was provided, ask the user for a YouTube or Instagram Reel URL.

## Workflow

1. Call the `summarize_video` tool with the provided URL
2. Read the returned transcript carefully
3. Extract the **key lessons** as succinctly as possible
4. For each lesson, provide **clear, actionable steps** on how to carry it out
5. Keep the summary concise and scannable — use bullet points and short paragraphs

## Supported URLs

- `youtube.com/watch?v=...`
- `youtu.be/...`
- `instagram.com/reel/...`

## Notes

- Short videos (under 2 minutes) will complete in a few seconds
- Longer videos (10+ minutes) may take up to 60 seconds to transcribe
- If the video has no speech, the tool will report that no speech was detected
