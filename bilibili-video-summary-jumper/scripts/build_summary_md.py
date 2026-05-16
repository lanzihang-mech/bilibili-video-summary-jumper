#!/usr/bin/env python3
"""Build an editable Markdown video summary from SRT and frame evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


TIME_RE = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{1,3})\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{1,3})"
)


def parse_time(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    seconds = float(parts[-1])
    minutes = int(parts[-2]) if len(parts) >= 2 else 0
    hours = int(parts[-3]) if len(parts) >= 3 else 0
    return hours * 3600 + minutes * 60 + seconds


def display_time(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_srt(path: Path) -> list[dict[str, object]]:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    cues: list[dict[str, object]] = []
    i = 0
    while i < len(lines):
        match = TIME_RE.search(lines[i])
        if not match:
            i += 1
            continue
        start = parse_time(match.group("start"))
        end = parse_time(match.group("end"))
        i += 1
        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            if not lines[i].strip().isdigit():
                text_lines.append(lines[i].strip())
            i += 1
        text = " ".join(text_lines).strip()
        if text:
            cues.append({"start_seconds": start, "end_seconds": end, "text": text})
        i += 1
    return cues


def chunk_cues(cues: list[dict[str, object]], interval: int) -> list[dict[str, object]]:
    chunks: list[dict[str, object]] = []
    current: list[dict[str, object]] = []
    chunk_start = float(cues[0]["start_seconds"]) if cues else 0
    for cue in cues:
        start = float(cue["start_seconds"])
        if current and start - chunk_start >= interval:
            chunks.append(make_chunk(current))
            current = []
            chunk_start = start
        current.append(cue)
    if current:
        chunks.append(make_chunk(current))
    return chunks


def make_chunk(cues: list[dict[str, object]]) -> dict[str, object]:
    text = " ".join(str(cue["text"]) for cue in cues)
    summary = text if len(text) <= 220 else text[:217].rstrip() + "..."
    return {
        "start_seconds": float(cues[0]["start_seconds"]),
        "end_seconds": float(cues[-1]["end_seconds"]),
        "summary": summary,
    }


def nearest_frame(frames: list[dict[str, object]], seconds: float) -> str:
    if not frames:
        return ""
    frame = min(frames, key=lambda item: abs(float(item["time_seconds"]) - seconds))
    return str(frame["file"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Markdown summary from SRT and frames.")
    parser.add_argument("srt")
    parser.add_argument("--frames", required=True, help="Frame directory containing frames.json")
    parser.add_argument("--video-title", default="视频总结")
    parser.add_argument("--output", default="video-summary.md")
    parser.add_argument("--chunk-seconds", type=int, default=30)
    args = parser.parse_args()

    srt = Path(args.srt)
    frame_dir = Path(args.frames)
    cues = parse_srt(srt)
    if not cues:
        raise SystemExit("No SRT cues found.")
    frames_json = frame_dir / "frames.json"
    frames = json.loads(frames_json.read_text(encoding="utf-8")) if frames_json.exists() else []
    chunks = chunk_cues(cues, args.chunk_seconds)
    duration = float(cues[-1]["end_seconds"])

    lines = [
        f"# {args.video_title}",
        "",
        "## 视频信息",
        f"- 字幕段数：{len(cues)}",
        f"- 估计时长：{display_time(duration)}",
        f"- 关键截图：{len(frames)}",
        "",
        "## 总览",
        f"- 本视频围绕「{args.video_title}」展开，以下总结基于本地 ASR 字幕和截图证据生成。",
        "- 时间线用于快速定位原视频中的论述位置，截图用于辅助确认上下文。",
        "- 若 ASR 存在错字，优先以视频画面和人工复核为准。",
        "",
        "## 章节目录",
    ]
    for index, chunk in enumerate(chunks, start=1):
        lines.append(f"- [{display_time(float(chunk['start_seconds']))}](#t{int(float(chunk['start_seconds']))}) 片段 {index}")

    lines.extend(["", "## 时间线证据"])
    for index, chunk in enumerate(chunks, start=1):
        start = float(chunk["start_seconds"])
        frame = nearest_frame(frames, start)
        lines.extend(
            [
                "",
                f"### <a id=\"t{int(start)}\"></a>{display_time(start)} 片段 {index}",
                f"- time: {int(start)}",
                f"- frame: {frame}",
                f"- summary: {chunk['summary']}",
            ]
        )
        if frame:
            lines.append(f"![{display_time(start)}]({Path('frames') / frame})")

    lines.extend(["", "## 关键观点"])
    for chunk in chunks[:6]:
        lines.append(f"- {display_time(float(chunk['start_seconds']))}：{chunk['summary']}")

    lines.extend(["", "## 可复用引用"])
    for chunk in chunks[:12]:
        lines.append(f"- {display_time(float(chunk['start_seconds']))} {chunk['summary']}")

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
