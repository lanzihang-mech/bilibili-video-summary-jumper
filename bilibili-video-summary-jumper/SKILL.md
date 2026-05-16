---
name: bilibili-video-summary-jumper
description: Generate visual single-file HTML summaries for Bilibili videos with timestamp links back to the original Bilibili page. Use when Codex is asked to summarize a Bilibili video, create a video timeline, make a jumpable HTML summary, process Bilibili subtitles, or build a non-embedded video summary page from Bilibili subtitles and timestamps.
---

# Bilibili Video Summary Jumper

Create a single HTML summary for a Bilibili video without downloading or embedding the source video. The output should make the transcript skimmable and every important moment should link back to the original Bilibili video at the right timestamp.

## Workflow

1. Fetch subtitles with `scripts/fetch_bili_subtitles.py`.
   - Prefer automatic subtitle fetch through `yt-dlp`.
   - If `yt-dlp` is missing or Bilibili exposes no subtitle track, ask the user for SRT/VTT copied from vCaptions or `bili-subtitle-copier`.
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

Build HTML from a subtitle file:

```bash
python scripts/build_summary_html.py "https://www.bilibili.com/video/BV...?p=2" out/subtitle.vtt --title "Video title" --output out/summary.html
```

If automatic fetching fails, save copied SRT/VTT text to a file and run `build_summary_html.py` directly.

## Output Standards

- Generate one self-contained `.html` file.
- Include video metadata, a 3-5 sentence overview, chapter navigation, timestamp cards, key points, and a copyable citation area.
- Make timestamps obvious: every timeline card must show the source time and a "跳转" style action.
- Keep the layout dense enough for review work, not a landing page.
- Do not embed `<video>`, `<iframe>`, or copied video media.

## Resources

- `scripts/fetch_bili_subtitles.py`: detects and downloads available Bilibili subtitles via `yt-dlp`.
- `scripts/build_summary_html.py`: parses SRT/VTT, normalizes timestamps, and renders the HTML.
- `assets/template.html`: single-file visual summary template.
- `references/subtitle-sources.md`: fallback subtitle source notes and troubleshooting.
