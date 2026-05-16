#!/usr/bin/env python3
"""Transcribe a user-provided MP4 into SRT and normalized transcript JSON."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise SystemExit("ffmpeg not found. Install ffmpeg or imageio-ffmpeg.") from exc


def run(args: list[str]) -> None:
    result = subprocess.run(args, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise SystemExit((result.stdout + result.stderr)[-4000:])


def srt_time(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_srt(cues: list[dict[str, object]], path: Path) -> None:
    lines: list[str] = []
    for index, cue in enumerate(cues, start=1):
        text = str(cue["text"]).strip()
        if not text:
            continue
        start = float(cue["start_seconds"])
        end = max(float(cue["end_seconds"]), start + 0.5)
        lines.extend([str(index), f"{srt_time(start)} --> {srt_time(end)}", text, ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcribe local MP4 to SRT and transcript JSON.")
    parser.add_argument("mp4", help="Local MP4 file")
    parser.add_argument("--output-dir", default="out/video", help="Output directory")
    parser.add_argument("--model", default="small", help="faster-whisper model size")
    parser.add_argument("--device", default="cpu", help="faster-whisper device")
    parser.add_argument("--compute-type", default="int8", help="faster-whisper compute type")
    parser.add_argument("--language", default="zh", help="Language code, empty for auto")
    parser.add_argument("--keep-audio", action="store_true", help="Keep extracted wav in output directory")
    args = parser.parse_args()

    mp4 = Path(args.mp4)
    if not mp4.exists():
        raise SystemExit(f"MP4 not found: {mp4}")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()

    audio_temp = tempfile.TemporaryDirectory(prefix="mp4-summary-asr-")
    audio_path = Path(audio_temp.name) / "audio.wav"
    try:
        run([ffmpeg, "-y", "-i", str(mp4), "-vn", "-ac", "1", "-ar", "16000", str(audio_path)])
        from faster_whisper import WhisperModel

        model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
        segments_iter, info = model.transcribe(str(audio_path), language=args.language or None, vad_filter=True)
        cues: list[dict[str, object]] = []
        for segment in segments_iter:
            text = segment.text.strip()
            if text:
                cues.append(
                    {
                        "start_seconds": float(segment.start),
                        "end_seconds": float(segment.end),
                        "text": text,
                    }
                )
        if not cues:
            raise SystemExit("ASR produced no transcript cues.")

        srt_path = output_dir / "video.srt"
        json_path = output_dir / "transcript.json"
        write_srt(cues, srt_path)
        json_path.write_text(
            json.dumps(
                {
                    "source_mp4": str(mp4),
                    "model": args.model,
                    "device": args.device,
                    "compute_type": args.compute_type,
                    "language": getattr(info, "language", args.language),
                    "duration": getattr(info, "duration", None),
                    "cues": cues,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if args.keep_audio:
            shutil.copy2(audio_path, output_dir / "audio.wav")
        print(str(srt_path))
        print(str(json_path))
        return 0
    finally:
        audio_temp.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
