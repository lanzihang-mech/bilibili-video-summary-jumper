#!/usr/bin/env python3
"""Extract timestamped screenshots from a local MP4 using an SRT timeline."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path


TIME_RE = re.compile(r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{1,3})\s*-->")


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise SystemExit("ffmpeg not found. Install ffmpeg or imageio-ffmpeg.") from exc


def parse_time(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    seconds = float(parts[-1])
    minutes = int(parts[-2]) if len(parts) >= 2 else 0
    hours = int(parts[-3]) if len(parts) >= 3 else 0
    return hours * 3600 + minutes * 60 + seconds


def format_stamp(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}-{minutes:02d}-{secs:02d}"


def read_srt_starts(path: Path) -> list[float]:
    starts: list[float] = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        match = TIME_RE.search(line)
        if match:
            starts.append(parse_time(match.group("start")))
    return starts


def select_times(starts: list[float], interval: int, max_frames: int) -> list[float]:
    if not starts:
        return []
    selected = [starts[0]]
    last = starts[0]
    for start in starts[1:]:
        if start - last >= interval:
            selected.append(start)
            last = start
        if len(selected) >= max_frames:
            break
    return selected


def run(args: list[str]) -> None:
    result = subprocess.run(args, text=True, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        raise SystemExit((result.stdout + result.stderr)[-4000:])


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract timeline frames from local MP4.")
    parser.add_argument("mp4")
    parser.add_argument("srt")
    parser.add_argument("--output-dir", default="out/video/frames")
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--max-frames", type=int, default=24)
    parser.add_argument("--width", type=int, default=960)
    args = parser.parse_args()

    mp4 = Path(args.mp4)
    srt = Path(args.srt)
    if not mp4.exists():
        raise SystemExit(f"MP4 not found: {mp4}")
    if not srt.exists():
        raise SystemExit(f"SRT not found: {srt}")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    times = select_times(read_srt_starts(srt), args.interval, args.max_frames)
    manifest = []
    for index, seconds in enumerate(times, start=1):
        filename = f"frame-{index:03d}-{format_stamp(seconds)}.jpg"
        frame_path = output_dir / filename
        run(
            [
                ffmpeg,
                "-y",
                "-ss",
                f"{seconds:.3f}",
                "-i",
                str(mp4),
                "-frames:v",
                "1",
                "-vf",
                f"scale={args.width}:-2",
                "-q:v",
                "3",
                str(frame_path),
            ]
        )
        manifest.append({"index": index, "time_seconds": seconds, "file": filename})
    (output_dir / "frames.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output_dir))
    print(str(output_dir / "frames.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
