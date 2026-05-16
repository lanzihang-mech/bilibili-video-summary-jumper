---
name: bilibili-video-summary-jumper
description: Generate visual single-file HTML summaries for Bilibili videos with timestamp links back to the original Bilibili page. Use when Codex is asked to summarize a Bilibili video, create a video timeline, make a jumpable HTML summary, process Bilibili subtitles, or build a non-embedded video summary page from Bilibili subtitles and timestamps.
---

# Bilibili Video Summary Jumper

Create a single HTML summary for a Bilibili video without downloading or embedding the source video. The output should make the transcript skimmable and every important moment should link back to the original Bilibili video at the right timestamp.

## Workflow

1. Fetch or create subtitles.
   - First run `scripts/fetch_bili_subtitles.py`; it checks Bilibili's public subtitle API and then `yt-dlp`.
   - If the user already has SRT/VTT from vCaptions or `bili-subtitle-copier`, skip fetching and use that file directly.
   - If no subtitle is available, run `scripts/transcribe_bili_asr.py` to extract temporary audio and generate timestamped subtitles with local ASR.
   - For multi-part videos where ASR would be too slow, use `scripts/build_bili_catalog_html.py` to create a navigable catalog summary from public Bilibili metadata, then transcribe specific `?p=` parts later.
   - Do not download, embed, mirror, or redistribute the video.
2. Build the HTML with `scripts/build_summary_html.py`.
   - Pass the Bilibili video URL, subtitle file, title, and output path.
   - Use the generated normalized transcript JSON when deeper AI summarization is needed.
   - Keep timestamp links as external links to Bilibili with `t=<seconds>`.
3. Improve the generated summary when useful.
   - Read the normalized transcript JSON.
   - Replace or supplement the heuristic overview, chapter labels, and key points.
   - Preserve all jump links and source timestamps.
4. Verify the output.
   - Open or inspect the HTML.
   - Confirm important cards have Bilibili links with `t=` and that `p=` is preserved for multi-part URLs.
   - Confirm no original video is embedded in the HTML.

## Quick Commands

Fetch subtitles:

```bash
python scripts/fetch_bili_subtitles.py "https://www.bilibili.com/video/BV..." --output-dir out
```

Generate subtitles and HTML with local ASR when no subtitle exists:

```bash
python scripts/transcribe_bili_asr.py "https://www.bilibili.com/video/BV...?p=3" --page 3 --title "Video title" --output-dir out/asr
```

Build HTML from a subtitle file:

```bash
python scripts/build_summary_html.py "https://www.bilibili.com/video/BV...?p=2" out/subtitle.vtt --title "Video title" --output out/summary.html
```

If automatic fetching fails, save copied SRT/VTT text to a file and run `build_summary_html.py` directly.

Build a fallback catalog summary from Bilibili metadata:

```bash
python scripts/build_bili_catalog_html.py "https://www.bilibili.com/video/BV..." --output out/catalog-summary.html
```

## Dependencies and Safety

- Required for automatic subtitle fetch: `yt-dlp`.
- Required for local ASR: `yt-dlp`, `ffmpeg` (or `imageio-ffmpeg`), and either `faster-whisper` or `openai-whisper`.
- Local ASR defaults to CPU `int8`; use `--device cuda --compute-type float16` only when CUDA is installed and working.
- Default ASR behavior uses temporary audio and deletes it after generating SRT, JSON, and HTML.
- Do not read browser cookies automatically. If login state is needed, only use a cookie file explicitly exported and provided by the user through `--cookies`.
- For multi-part videos, prefer a specific `?p=` URL and pass `--page`; do not transcribe a long playlist unless the user explicitly asks for it.

## Output Standards

- Generate one self-contained `.html` file.
- Include video metadata, a 3-5 sentence overview, chapter navigation, timestamp cards, key points, and a copyable citation area.
- Make timestamps obvious: every timeline card must show the source time and a "跳转" style action.
- Keep the layout dense enough for review work, not a landing page.
- Do not embed `<video>`, `<iframe>`, or copied video media.

## Resources

- `scripts/fetch_bili_subtitles.py`: detects and downloads available Bilibili subtitles via `yt-dlp`.
- `scripts/build_summary_html.py`: parses SRT/VTT, normalizes timestamps, and renders the HTML.
- `scripts/build_bili_catalog_html.py`: fallback renderer for multi-part videos with no public subtitles.
- `scripts/transcribe_bili_asr.py`: local ASR fallback that extracts temporary audio and generates SRT, JSON, and HTML.
- `assets/template.html`: single-file visual summary template.
- `references/subtitle-sources.md`: fallback subtitle source notes and troubleshooting.
