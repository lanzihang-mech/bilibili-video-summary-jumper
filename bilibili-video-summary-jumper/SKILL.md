---
name: bilibili-video-summary-jumper
description: Build jumpable local-video summary artifacts from a user-provided MP4. Use when Codex is asked to process an MP4 video into SRT subtitles, timestamped screenshots, a Markdown video summary, and a visual HTML summary whose controls jump within the local video at matching timestamps.
---

# Bilibili Video Summary Jumper

Use this skill when the user provides a local MP4. The skill creates transcript evidence, frame evidence, a Markdown summary, and a standalone HTML page whose buttons jump within the local video.

## Workflow

1. Run the full pipeline unless the user asks for a single step:

```bash
python scripts/run_pipeline.py "<video.mp4>" --output-dir out/<slug>
```

2. The pipeline performs:
   - `transcribe_mp4.py`: extract audio from the MP4 and create `video.srt` plus `transcript.json` with `faster-whisper`.
   - `extract_frames.py`: capture timestamped `.jpg` frames from the MP4 using the SRT timeline.
   - `build_summary_md.py`: create `video-summary.md` from transcript chunks and frame references.
   - `build_jump_html.py`: render `video-summary.html` with a local video player and timestamp jump buttons.

3. Verify the result:
   - HTML should include one local `<video>` player.
   - Every timeline/evidence card must have a `data-time` jump button.
   - Do not use Bilibili web links unless the user explicitly asks for `--jump-target bilibili`.
   - Markdown should include video info, overview, chapters, timeline evidence, key points, and reusable citations.

## Step Commands

Transcribe only:

```bash
python scripts/transcribe_mp4.py "<video.mp4>" --output-dir out/<slug> --model small
```

Extract frames only:

```bash
python scripts/extract_frames.py "<video.mp4>" out/<slug>/video.srt --output-dir out/<slug>/frames
```

Build Markdown only:

```bash
python scripts/build_summary_md.py out/<slug>/video.srt --frames out/<slug>/frames --video-title "Video title" --output out/<slug>/video-summary.md
```

Build HTML only:

```bash
python scripts/build_jump_html.py out/<slug>/video-summary.md --local-video "<video.mp4>" --output out/<slug>/video-summary.html
```

## Defaults

- ASR model: `small`.
- ASR device: CPU.
- ASR compute type: `int8`.
- Frame interval: about one frame every 30 seconds, anchored to transcript timestamps.
- Output target: local video player jump buttons.
- Source media: user-provided MP4 only. Do not fetch or download Bilibili media.

## Resources

- `scripts/run_pipeline.py`: complete MP4-to-HTML workflow.
- `scripts/transcribe_mp4.py`: MP4 audio extraction and local ASR.
- `scripts/extract_frames.py`: timestamped screenshot extraction.
- `scripts/build_summary_md.py`: Markdown summary generation.
- `scripts/build_jump_html.py`: Markdown-to-HTML renderer with Bilibili timestamp links.
- `references/workflow.md`: implementation notes and troubleshooting.
