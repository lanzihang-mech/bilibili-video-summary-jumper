# Subtitle Sources

Primary source: `yt-dlp`.

- Use `--list-subs` first to inspect available subtitle tracks.
- Use `--skip-download`, `--write-subs`, `--write-auto-subs`, `--sub-langs all,-danmaku`, and `--sub-format vtt/srt` to avoid video download.
- Some Bilibili videos require login cookies or expose no subtitles. Treat that as a normal fallback path, not a script bug.

Fallback sources:

- vCaptions or similar browser extensions that can copy subtitles with timestamps.
- `bili-subtitle-copier`, a Bilibili AI subtitle panel helper that copies SRT text from the visible page.

Accepted fallback formats:

- SRT blocks with `00:00:01,000 --> 00:00:03,000`.
- WebVTT blocks with `00:00:01.000 --> 00:00:03.000`.

Do not use downloaded video or audio as the default workflow. This skill is for transcript-based summaries and external timestamp jumps only.
