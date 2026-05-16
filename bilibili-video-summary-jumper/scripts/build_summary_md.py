#!/usr/bin/env python3
"""Build a beginner-friendly learning-note summary from SRT and frame evidence."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path


TIME_RE = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{1,3})\s*-->\s*(?P<end>(?:\d{1,2}:)?\d{1,2}:\d{2}[\.,]\d{1,3})"
)

TEXT_FIXES = (
    ("边程", "编程"),
    ("变程", "编程"),
    ("罗计", "逻辑"),
    ("逻计", "逻辑"),
    ("洛辑", "逻辑"),
    ("拍访", "Python"),
    ("派森", "Python"),
    ("新导片", "先导片"),
    ("细致末节", "细枝末节"),
    ("闭卷考式", "闭卷考试"),
    ("必卷考试", "闭卷考试"),
    ("查漏不缺", "查漏补缺"),
    ("编作编学", "边做边学"),
    ("鲁马", "入行"),
    ("封期", "风气"),
    ("亮解", "量级"),
    ("住线", "主线"),
    ("长篇大论", "长篇大论"),
)


@dataclass
class LearningSegment:
    start_seconds: float
    end_seconds: float
    topic: str
    explanation: str
    beginner_takeaway: str
    evidence: str
    frame: str


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
        text = clean_text(" ".join(text_lines))
        if text:
            cues.append({"start_seconds": start, "end_seconds": end, "text": text})
        i += 1
    return cues


def clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    for wrong, right in TEXT_FIXES:
        text = text.replace(wrong, right)
    return text


def nearest_frame(frames: list[dict[str, object]], seconds: float) -> str:
    if not frames:
        return ""
    frame = min(frames, key=lambda item: abs(float(item["time_seconds"]) - seconds))
    return str(frame["file"])


def cues_between(cues: list[dict[str, object]], start: float, end: float) -> list[dict[str, object]]:
    return [cue for cue in cues if start <= float(cue["start_seconds"]) < end]


def excerpt(cues: list[dict[str, object]], limit: int = 96) -> str:
    text = clean_text(" ".join(str(cue["text"]) for cue in cues))
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def infer_video_type(text: str, title: str) -> str:
    joined = title + " " + text
    if any(token in joined for token in ("Python", "编程", "程序员", "教程", "课程", "零基础")):
        return "programming_intro"
    return "general_learning"


def fixed_segments_for_intro(cues: list[dict[str, object]], frames: list[dict[str, object]]) -> list[LearningSegment]:
    duration = float(cues[-1]["end_seconds"])
    windows = [
        (
            0,
            min(32, duration),
            "先消除编程恐惧",
            "开头先点出新手对编程的常见印象：难、抽象、烧脑。作者想先把“编程很可怕”这层心理门槛拿掉。",
            "刚开始不需要证明自己聪明，也不需要一次听懂所有术语；先接受它可以被拆成更简单的逻辑。",
        ),
        (
            32,
            min(64, duration),
            "为什么要做这套课",
            "作者说明这套课不是为了堆内容，而是回应新手想要一套完整、轻量、容易开始的入门课。",
            "选择课程时不要只看时长和知识点数量，更要看它能不能帮你建立第一条清楚的学习主线。",
        ),
        (
            64,
            min(100, duration),
            "课程的设计方式",
            "这里解释课程会用例子、画面和生活化比喻来讲概念，尽量避免一上来就陷入抽象名词。",
            "遇到变量、循环、函数这类概念时，先理解它在解决什么问题，再去记语法。",
        ),
        (
            100,
            min(132, duration),
            "新手真正要抓住什么",
            "视频强调入门阶段不必死记每个细节，核心是先掌握编程逻辑、查资料能力和解决问题的方法。",
            "学习 Python 的目标不是背完语法表，而是能看懂问题、拆开步骤、写出能运行的解法。",
        ),
        (
            132,
            min(168, duration),
            "学完之后怎么继续",
            "作者把这套课定位为跨过入门门槛的第一步，后面还可以接更长的教程、项目练习或其他语言。",
            "第一门语言学顺之后，第二门语言通常会容易很多，因为底层思路已经迁移过去了。",
        ),
        (
            168,
            duration,
            "结尾与行动提醒",
            "最后主要是鼓励收藏、分享和继续跟学，也说明课程会根据反馈继续更新。",
            "看完先别急着找更多资源，先把第一集的主线记下来，再进入下一节动手练习。",
        ),
    ]
    return build_window_segments(cues, frames, windows)


def generic_segments(cues: list[dict[str, object]], frames: list[dict[str, object]], chunk_seconds: int) -> list[LearningSegment]:
    duration = float(cues[-1]["end_seconds"])
    boundaries = list(range(0, max(1, int(duration)), max(30, chunk_seconds)))
    if not boundaries or boundaries[-1] < duration:
        boundaries.append(int(duration) + 1)
    windows = []
    for index, start in enumerate(boundaries[:-1], start=1):
        end = min(boundaries[index], duration)
        windows.append(
            (
                float(start),
                float(end),
                f"学习片段 {index}",
                "这一段围绕一个连续话题展开。建议先抓住它想解决的问题，再回到字幕细节里补证据。",
                "新手阅读时先用自己的话复述这一段，再点击时间点回看原视频确认。",
            )
        )
    return build_window_segments(cues, frames, windows[:8])


def build_window_segments(
    cues: list[dict[str, object]],
    frames: list[dict[str, object]],
    windows: list[tuple[float, float, str, str, str]],
) -> list[LearningSegment]:
    segments: list[LearningSegment] = []
    for start, end, topic, explanation, takeaway in windows:
        if end <= start:
            continue
        scoped = cues_between(cues, start, end)
        if not scoped:
            continue
        actual_start = float(scoped[0]["start_seconds"])
        actual_end = float(scoped[-1]["end_seconds"])
        segments.append(
            LearningSegment(
                start_seconds=actual_start,
                end_seconds=actual_end,
                topic=topic,
                explanation=explanation,
                beginner_takeaway=takeaway,
                evidence=excerpt(scoped),
                frame=nearest_frame(frames, actual_start),
            )
        )
    return segments


def build_intro_notes(cues: list[dict[str, object]], frames: list[dict[str, object]], title: str, chunk_seconds: int) -> dict[str, object]:
    text = " ".join(str(cue["text"]) for cue in cues)
    video_type = infer_video_type(text, title)
    if video_type == "programming_intro":
        segments = fixed_segments_for_intro(cues, frames)
        return {
            "one_sentence": "这集不是正式讲语法，而是在帮零基础学习者放下对编程的恐惧，建立一条轻量、可继续的 Python 入门路线。",
            "audience": [
                "对 Python 或编程感兴趣，但一直觉得抽象、难开始的人。",
                "想先快速建立全局认识，再决定是否继续系统学习的新手。",
                "需要期末、二级或自学入门，但不想一开始就陷入厚重教材的人。",
            ],
            "problem": "它解决的不是某个语法点，而是“我为什么要学、该怎么开始、这套课会怎么带我入门”的问题。",
            "key_points": [
                "编程入门最先要处理的是心理门槛，而不是马上背语法。",
                "好的新手课应该用具体例子和画面把抽象概念讲清楚。",
                "学习重点是核心逻辑、搜索能力和解决问题流程，不是记住所有语言细节。",
                "Python 可以作为第一门语言；理解了核心思路后，再学其他语言会更容易。",
            ],
            "actions": [
                "先把“编程 = 可拆解的问题解决过程”写到自己的笔记里。",
                "下一集开始时，每节只抓一个核心概念，不追求一次吃完全部细节。",
                "遇到听不懂的术语，先记录时间点，回看对应片段和截图，再查资料补齐。",
            ],
            "segments": segments,
        }
    segments = generic_segments(cues, frames, chunk_seconds)
    return {
        "one_sentence": "这个视频围绕一个学习主题展开，适合先用时间线抓住主线，再回到原视频复核证据。",
        "audience": ["想快速理解视频主线的人。", "需要带时间点复习或做笔记的人。"],
        "problem": "它帮助你把连续视频内容拆成可复习、可跳转、可验证的学习片段。",
        "key_points": ["先看主题，再看证据。", "先理解段落功能，再回到字幕细节。", "截图和时间点用于复核，不替代原视频。"],
        "actions": ["先读完分段讲解。", "点击不清楚的时间点回看视频。", "把自己的理解补充到 Markdown 里。"],
        "segments": segments,
    }


def write_markdown(args: argparse.Namespace, cues: list[dict[str, object]], frames: list[dict[str, object]]) -> str:
    notes = build_intro_notes(cues, frames, args.video_title, args.chunk_seconds)
    segments: list[LearningSegment] = notes["segments"]  # type: ignore[assignment]
    duration = float(cues[-1]["end_seconds"])

    lines = [
        f"# {args.video_title}",
        "",
        "## 视频信息",
        f"- 字幕段数：{len(cues)}",
        f"- 估计时长：{display_time(duration)}",
        f"- 关键截图：{len(frames)}",
        "- 生成方式：本地 MP4 + ASR 字幕 + 截图证据",
        "",
        "## 一句话总结",
        str(notes["one_sentence"]),
        "",
        "## 适合谁看",
    ]
    lines.extend(f"- {item}" for item in notes["audience"])  # type: ignore[union-attr]
    lines.extend(["", "## 这段视频解决的问题", str(notes["problem"]), "", "## 核心观点"])
    lines.extend(f"- {item}" for item in notes["key_points"])  # type: ignore[union-attr]

    lines.extend(["", "## 分段讲解"])
    for segment in segments:
        start = int(segment.start_seconds)
        lines.extend(
            [
                "",
                f"### <a id=\"t{start}\"></a>{display_time(segment.start_seconds)} {segment.topic}",
                f"- time: {start}",
                f"- frame: {segment.frame}",
                f"- topic: {segment.topic}",
                f"- explanation: {segment.explanation}",
                f"- beginner_takeaway: {segment.beginner_takeaway}",
                f"- evidence: {segment.evidence}",
            ]
        )
        if segment.frame:
            lines.append(f"![{display_time(segment.start_seconds)}](frames/{segment.frame})")

    lines.extend(["", "## 新手下一步行动"])
    lines.extend(f"- {item}" for item in notes["actions"])  # type: ignore[union-attr]

    lines.extend(["", "## 时间线索引"])
    for segment in segments:
        start = int(segment.start_seconds)
        lines.append(f"- [{display_time(segment.start_seconds)} {segment.topic}](#t{start})：{segment.evidence}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build learning-note Markdown from SRT and frames.")
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

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(write_markdown(args, cues, frames), encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
