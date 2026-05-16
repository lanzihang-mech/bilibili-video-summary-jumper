#!/usr/bin/env python3
"""Run the complete local MP4 to Bilibili-jump HTML summary pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(args: list[str]) -> None:
    result = subprocess.run(args, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise SystemExit((result.stdout + result.stderr)[-4000:])
    if result.stdout.strip():
        sys.stdout.buffer.write((result.stdout.strip() + "\n").encode("utf-8", errors="replace"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SRT, frames, Markdown, and jumpable HTML from a local MP4.")
    parser.add_argument("mp4")
    parser.add_argument("--source-url", default=None)
    parser.add_argument("--jump-target", choices=["local", "bilibili"], default="local")
    parser.add_argument("--output-dir", default="out/video")
    parser.add_argument("--title", default=None)
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--frame-interval", type=int, default=30)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    mp4 = Path(args.mp4)
    title = args.title or mp4.stem
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    srt = output_dir / "video.srt"
    frames = output_dir / "frames"
    summary_md = output_dir / "video-summary.md"
    summary_html = output_dir / "video-summary.html"

    run(
        [
            sys.executable,
            str(script_dir / "transcribe_mp4.py"),
            str(mp4),
            "--output-dir",
            str(output_dir),
            "--model",
            args.model,
            "--device",
            args.device,
            "--compute-type",
            args.compute_type,
        ]
    )
    run(
        [
            sys.executable,
            str(script_dir / "extract_frames.py"),
            str(mp4),
            str(srt),
            "--output-dir",
            str(frames),
            "--interval",
            str(args.frame_interval),
        ]
    )
    run(
        [
            sys.executable,
            str(script_dir / "build_summary_md.py"),
            str(srt),
            "--frames",
            str(frames),
            "--video-title",
            title,
            "--output",
            str(summary_md),
            "--chunk-seconds",
            str(args.frame_interval),
        ]
    )
    html_args = [
            sys.executable,
            str(script_dir / "build_jump_html.py"),
            str(summary_md),
            "--output",
            str(summary_html),
            "--title",
            title,
    ]
    if args.jump_target == "local":
        html_args.extend(["--local-video", str(mp4)])
    else:
        if not args.source_url:
            raise SystemExit("--source-url is required when --jump-target bilibili.")
        html_args.extend(["--source-url", args.source_url])
    run(html_args)
    sys.stdout.buffer.write((str(summary_html) + "\n").encode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
