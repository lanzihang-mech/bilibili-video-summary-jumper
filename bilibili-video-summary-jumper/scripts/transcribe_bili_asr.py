#!/usr/bin/env python3
"""Generate timestamped subtitles and an HTML summary from Bilibili audio via local ASR."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, encoding="utf-8", errors="replace")


def find_executable(explicit_path: str | None, name: str) -> str | None:
    if explicit_path:
        candidate = Path(explicit_path)
        if candidate.exists():
            return str(candidate)
        return explicit_path
    return shutil.which(name)


def find_ffmpeg() -> str | None:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def format_srt_time(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(segments: list[dict[str, object]], output_path: Path) -> None:
    lines: list[str] = []
    for index, segment in enumerate(segments, start=1):
        text = str(segment.get("text", "")).strip()
        if not text:
            continue
        start = float(segment.get("start_seconds", 0))
        end = max(float(segment.get("end_seconds", start + 0.5)), start + 0.5)
        lines.extend([str(index), f"{format_srt_time(start)} --> {format_srt_time(end)}", text, ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")


def download_audio(
    url: str,
    output_dir: Path,
    yt_dlp: str,
    ffmpeg: str,
    cookies: str | None,
    page: int | None,
) -> Path:
    output_template = output_dir / "%(id)s.p%(playlist_index|1)s.%(ext)s"
    cmd = [
        yt_dlp,
        "--no-playlist" if page is None else "--yes-playlist",
        "-f",
        "bestaudio/best",
        "--extract-audio",
        "--audio-format",
        "wav",
        "--audio-quality",
        "0",
        "--ffmpeg-location",
        ffmpeg,
        "--output",
        str(output_template),
    ]
    if page is not None:
        cmd.extend(["--playlist-items", str(page)])
    if cookies:
        cmd.extend(["--cookies", cookies])
    cmd.append(url)
    result = run_command(cmd)
    audio_files = sorted(output_dir.glob("*.wav"), key=lambda path: path.stat().st_mtime, reverse=True)
    if result.returncode != 0 or not audio_files:
        raise RuntimeError(
            "Audio extraction failed. Ensure yt-dlp and ffmpeg are installed, the URL is accessible, "
            "and pass --cookies exported_cookie.txt if Bilibili requires login.\n"
            + (result.stdout + result.stderr)[-4000:]
        )
    return audio_files[0]


def transcribe_with_faster_whisper(audio_path: Path, model_size: str, language: str | None) -> list[dict[str, object]]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Missing faster-whisper. Install with: python -m pip install faster-whisper") from exc

    model = WhisperModel(model_size, device="auto", compute_type="default")
    segments_iter, _info = model.transcribe(str(audio_path), language=language, vad_filter=True)
    segments: list[dict[str, object]] = []
    for segment in segments_iter:
        text = segment.text.strip()
        if text:
            segments.append({"start_seconds": float(segment.start), "end_seconds": float(segment.end), "text": text})
    return segments


def transcribe_with_openai_whisper(audio_path: Path, model_size: str, language: str | None) -> list[dict[str, object]]:
    try:
        import whisper
    except ImportError as exc:
        raise RuntimeError(
            "Missing ASR package. Install faster-whisper with: python -m pip install faster-whisper "
            "or OpenAI Whisper with: python -m pip install openai-whisper"
        ) from exc

    model = whisper.load_model(model_size)
    result = model.transcribe(str(audio_path), language=language)
    segments: list[dict[str, object]] = []
    for segment in result.get("segments", []):
        text = str(segment.get("text", "")).strip()
        if text:
            segments.append(
                {
                    "start_seconds": float(segment.get("start", 0)),
                    "end_seconds": float(segment.get("end", 0)),
                    "text": text,
                }
            )
    return segments


def build_html(url: str, srt_path: Path, title: str, output_html: Path) -> None:
    builder = Path(__file__).resolve().parent / "build_summary_html.py"
    result = run_command(
        [
            sys.executable,
            str(builder),
            url,
            str(srt_path),
            "--title",
            title,
            "--output",
            str(output_html),
            "--transcript-json",
            str(output_html.with_suffix(".transcript.json")),
        ]
    )
    if result.returncode != 0:
        raise RuntimeError("HTML generation failed.\n" + (result.stdout + result.stderr)[-4000:])


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe Bilibili audio locally and generate a jumpable HTML summary.")
    parser.add_argument("url", help="Bilibili video URL")
    parser.add_argument("--output-dir", default="out/asr", help="Directory for SRT, transcript JSON, and HTML")
    parser.add_argument("--title", default="Bilibili 本地 ASR 视频总结", help="HTML title")
    parser.add_argument("--page", type=int, default=None, help="Optional multi-part page number to transcribe")
    parser.add_argument("--cookies", default=None, help="Optional user-exported Bilibili cookies file")
    parser.add_argument("--yt-dlp", default=None, help="Path to yt-dlp executable")
    parser.add_argument("--model", default="small", help="ASR model size, e.g. tiny/base/small/medium")
    parser.add_argument("--language", default="zh", help="ASR language code; use empty string for auto")
    parser.add_argument("--engine", choices=["faster-whisper", "whisper"], default="faster-whisper")
    parser.add_argument("--keep-audio", action="store_true", help="Keep extracted temporary audio")
    args = parser.parse_args()

    yt_dlp = find_executable(args.yt_dlp, "yt-dlp")
    if not yt_dlp:
        print("ERROR: yt-dlp was not found. Install with: python -m pip install yt-dlp", file=sys.stderr)
        return 2
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print(
            "ERROR: ffmpeg was not found. Install ffmpeg and ensure it is on PATH, "
            "or install imageio-ffmpeg with: python -m pip install imageio-ffmpeg",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    language = args.language or None
    audio_root: Path
    temp_context = None
    if args.keep_audio:
        audio_root = output_dir / "audio"
        audio_root.mkdir(parents=True, exist_ok=True)
    else:
        temp_context = tempfile.TemporaryDirectory(prefix="bili-asr-")
        audio_root = Path(temp_context.name)

    try:
        audio_path = download_audio(args.url, audio_root, yt_dlp, ffmpeg, args.cookies, args.page)
        if args.engine == "faster-whisper":
            segments = transcribe_with_faster_whisper(audio_path, args.model, language)
        else:
            segments = transcribe_with_openai_whisper(audio_path, args.model, language)
        if not segments:
            raise RuntimeError("ASR produced no transcript segments.")

        stem = "asr"
        if args.page is not None:
            stem = f"p{args.page:02d}.asr"
        srt_path = output_dir / f"{stem}.srt"
        json_path = output_dir / f"{stem}.asr.json"
        html_path = output_dir / f"{stem}.summary.html"
        write_srt(segments, srt_path)
        json_path.write_text(
            json.dumps({"url": args.url, "title": args.title, "engine": args.engine, "model": args.model, "cues": segments}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        build_html(args.url, srt_path, args.title, html_path)
        manifest = {
            "url": args.url,
            "page": args.page,
            "title": args.title,
            "srt": str(srt_path),
            "asr_json": str(json_path),
            "html": str(html_path),
            "audio_kept": args.keep_audio,
            "audio": str(audio_path) if args.keep_audio else None,
        }
        (output_dir / f"{stem}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(str(srt_path))
        print(str(json_path))
        print(str(html_path))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        if temp_context is not None:
            temp_context.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
