#!/usr/bin/env python3
"""Build a visual Bilibili summary HTML from SRT or WebVTT subtitles."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TIME_RE = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{1,3})\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{1,3})"
)
TAG_RE = re.compile(r"<[^>]+>")


def parse_time(value: str) -> float:
    clean = value.replace(",", ".")
    parts = clean.split(":")
    seconds = float(parts[-1])
    minutes = int(parts[-2]) if len(parts) >= 2 else 0
    hours = int(parts[-3]) if len(parts) >= 3 else 0
    return hours * 3600 + minutes * 60 + seconds


def format_time(seconds: float) -> str:
    total = max(0, int(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def clean_text(lines: list[str]) -> str:
    joined = " ".join(line.strip() for line in lines if line.strip())
    joined = TAG_RE.sub("", joined)
    joined = re.sub(r"\s+", " ", joined).strip()
    return html.unescape(joined)


def parse_subtitles(path: Path) -> list[dict[str, object]]:
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
                text_lines.append(lines[i])
            i += 1
        text = clean_text(text_lines)
        if text:
            cues.append({"start_seconds": start, "end_seconds": max(end, start + 0.5), "text": text})
        i += 1
    return cues


def bilibili_jump_url(source_url: str, seconds: float) -> str:
    split = urlsplit(source_url)
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query["t"] = str(max(0, int(seconds)))
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


def make_chunks(cues: list[dict[str, object]], target_seconds: int = 90) -> list[dict[str, object]]:
    if not cues:
        return []
    chunks: list[dict[str, object]] = []
    current: list[dict[str, object]] = []
    chunk_start = float(cues[0]["start_seconds"])
    for cue in cues:
        cue_start = float(cue["start_seconds"])
        if current and cue_start - chunk_start >= target_seconds:
            chunks.append(chunk_from_cues(current))
            current = []
            chunk_start = cue_start
        current.append(cue)
        if len(current) >= 8:
            chunks.append(chunk_from_cues(current))
            current = []
            chunk_start = float(cue["end_seconds"])
    if current:
        chunks.append(chunk_from_cues(current))
    return chunks


def chunk_from_cues(cues: list[dict[str, object]]) -> dict[str, object]:
    text = " ".join(str(cue["text"]) for cue in cues)
    if len(text) > 180:
        text = text[:177].rstrip() + "..."
    return {
        "start_seconds": float(cues[0]["start_seconds"]),
        "end_seconds": float(cues[-1]["end_seconds"]),
        "text": text,
    }


def make_chapters(chunks: list[dict[str, object]], max_chapters: int = 8) -> list[dict[str, object]]:
    if not chunks:
        return []
    if len(chunks) <= max_chapters:
        selected = chunks
    else:
        step = max(1, len(chunks) // max_chapters)
        selected = chunks[::step][:max_chapters]
    chapters = []
    for index, chunk in enumerate(selected, start=1):
        title = str(chunk["text"]).split("。")[0].split(".")[0]
        title = title[:28].strip() or f"章节 {index}"
        chapters.append({"index": index, "title": title, "start_seconds": float(chunk["start_seconds"])})
    return chapters


def render_list_items(items: list[str]) -> str:
    return "\n".join(f"<li>{html.escape(item)}</li>" for item in items)


def render_html(template: str, replacements: dict[str, str]) -> str:
    output = template
    for key, value in replacements.items():
        output = output.replace("{{" + key + "}}", value)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Bilibili timestamp-jump HTML summary.")
    parser.add_argument("url", help="Original Bilibili URL")
    parser.add_argument("subtitle_file", help="SRT or VTT subtitle file")
    parser.add_argument("--title", default="Bilibili 视频总结", help="HTML title and video title")
    parser.add_argument("--output", default="summary.html", help="Output HTML path")
    parser.add_argument("--transcript-json", default=None, help="Optional normalized transcript JSON output path")
    parser.add_argument("--template", default=None, help="Optional template HTML path")
    args = parser.parse_args()

    subtitle_path = Path(args.subtitle_file)
    cues = parse_subtitles(subtitle_path)
    if not cues:
        raise SystemExit("No subtitle cues were parsed. Check that the file is valid SRT or WebVTT.")

    chunks = make_chunks(cues)
    chapters = make_chapters(chunks)
    duration = float(cues[-1]["end_seconds"])
    source_url = args.url

    transcript_json = Path(args.transcript_json) if args.transcript_json else Path(args.output).with_suffix(".transcript.json")
    transcript_json.parent.mkdir(parents=True, exist_ok=True)
    transcript_json.write_text(json.dumps({"url": source_url, "title": args.title, "cues": cues}, ensure_ascii=False, indent=2), encoding="utf-8")

    template_path = Path(args.template) if args.template else Path(__file__).resolve().parents[1] / "assets" / "template.html"
    template = template_path.read_text(encoding="utf-8")

    overview = [
        f"本页基于字幕时间戳生成，共解析 {len(cues)} 条字幕，覆盖约 {format_time(duration)}。",
        "时间线卡片保留原始证据位置，点击即可跳回 B 站对应秒数。",
        "当前摘要为脚本生成的初稿；如需更精细的观点提炼，可让 Codex 读取 transcript JSON 后改写总览和关键观点。",
    ]
    if len(cues) >= 12:
        overview.append(f"内容从 {format_time(float(cues[0]['start_seconds']))} 开始，到 {format_time(duration)} 结束，适合按章节快速回看。")

    key_points = []
    for chunk in chunks[:6]:
        key_points.append(
            f'<article class="point"><strong>{format_time(float(chunk["start_seconds"]))}</strong><p>{html.escape(str(chunk["text"]))}</p></article>'
        )

    chapter_nav = []
    for chapter in chapters:
        jump = bilibili_jump_url(source_url, float(chapter["start_seconds"]))
        chapter_nav.append(
            f'<a href="{html.escape(jump)}" target="_blank" rel="noopener"><span>{html.escape(str(chapter["title"]))}</span><span>{format_time(float(chapter["start_seconds"]))}</span></a>'
        )

    timeline = []
    for chunk in chunks:
        jump = bilibili_jump_url(source_url, float(chunk["start_seconds"]))
        timeline.append(
            '<article class="card">'
            f'<div class="time">{format_time(float(chunk["start_seconds"]))}</div>'
            f'<p>{html.escape(str(chunk["text"]))}</p>'
            f'<a class="jump" href="{html.escape(jump)}" target="_blank" rel="noopener">跳转</a>'
            '</article>'
        )

    citation_lines = [
        f"{format_time(float(chunk['start_seconds']))} {chunk['text']} {bilibili_jump_url(source_url, float(chunk['start_seconds']))}"
        for chunk in chunks[:12]
    ]

    html_output = render_html(
        template,
        {
            "TITLE": html.escape(args.title),
            "SOURCE_URL": html.escape(source_url),
            "CUE_COUNT": str(len(cues)),
            "DURATION": format_time(duration),
            "GENERATED_AT": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "CHAPTER_NAV": "\n".join(chapter_nav),
            "OVERVIEW": render_list_items(overview),
            "KEY_POINTS": "\n".join(key_points),
            "TIMELINE": "\n".join(timeline),
            "CITATION": html.escape("\n".join(citation_lines)),
        },
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_output, encoding="utf-8")
    print(str(output_path))
    print(str(transcript_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
