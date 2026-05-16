# Local MP4 Workflow

Inputs:

- A local MP4 file supplied by the user.
- The matching original Bilibili URL for jump links.

Outputs:

- `video.srt`: timestamped subtitles.
- `transcript.json`: normalized subtitle cues.
- `frames/*.jpg`: timestamped screenshots.
- `frames/frames.json`: frame manifest.
- `video-summary.md`: editable summary with evidence.
- `video-summary.html`: visual page with local-video jump buttons.

Operational notes:

- Use `imageio-ffmpeg` as the ffmpeg provider when system `ffmpeg` is unavailable.
- Use `faster-whisper` with CPU `int8` by default for Windows compatibility.
- For speed tests use `--model tiny`; for final outputs use `small` or higher.
- If audio libraries fail on non-ASCII paths, copy intermediate audio to an ASCII temporary directory internally.
- Do not auto-read browser cookies and do not download source media from Bilibili.
- Use Bilibili external links only when the user explicitly asks for `--jump-target bilibili`.
