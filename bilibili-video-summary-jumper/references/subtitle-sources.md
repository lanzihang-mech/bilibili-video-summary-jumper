# Subtitle Sources

Primary source: `yt-dlp`.

- Before calling `yt-dlp`, check Bilibili's public subtitle path:
  - `https://api.bilibili.com/x/web-interface/view?bvid=<BV>` for `cid` and page metadata.
  - `https://api.bilibili.com/x/player/v2?bvid=<BV>&cid=<cid>` for `data.subtitle.subtitles`.
  - Each subtitle entry may expose `subtitle_url`, which returns JSON with `from`, `to`, and `content`.
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

Local ASR fallback:

- Use ASR only when public subtitles and user-provided SRT/VTT are unavailable.
- Extract audio only, never video frames, with `yt-dlp` and `ffmpeg`; `imageio-ffmpeg` can provide a Python-packaged ffmpeg fallback.
- Prefer `faster-whisper` for local transcription; `openai-whisper` is an alternate engine.
- Default `faster-whisper` settings are CPU `int8` for broad Windows compatibility. Use CUDA only when the machine has working CUDA libraries.
- Delete temporary audio by default. Keep audio only when the user explicitly asks for reusable cache or audit artifacts.
- For multi-part videos, transcribe one specified part at a time with `?p=` and `--page`.
