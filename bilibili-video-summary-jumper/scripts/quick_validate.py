#!/usr/bin/env python3
"""Quick static validation for generated local-video summary artifacts."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_MD_HEADINGS = (
    "## 一句话总结",
    "## 适合谁看",
    "## 这段视频解决的问题",
    "## 核心观点",
    "## 分段讲解",
    "## 新手下一步行动",
    "## 时间线索引",
)


def fail(message: str) -> None:
    raise SystemExit(f"quick_validate failed: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate generated summary Markdown and HTML.")
    parser.add_argument("output_dir", nargs="?", default=".")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    md_path = output_dir / "video-summary.md"
    html_path = output_dir / "video-summary.html"
    final_html_path = output_dir / "final-video-summary.html"
    if final_html_path.exists():
        html_path = final_html_path

    if not md_path.exists():
        fail(f"missing {md_path}")
    if not html_path.exists():
        fail(f"missing {html_path}")

    markdown = md_path.read_text(encoding="utf-8", errors="replace")
    html = html_path.read_text(encoding="utf-8", errors="replace")

    for heading in REQUIRED_MD_HEADINGS:
        if heading not in markdown:
            fail(f"missing Markdown heading {heading}")
    if "summary:" in markdown:
        fail("old raw subtitle timeline field `summary:` is still present")
    if not re.search(r"- explanation:\s*\S", markdown):
        fail("segment explanations are missing")
    if not re.search(r"- beginner_takeaway:\s*\S", markdown):
        fail("beginner takeaways are missing")
    if "<video" not in html:
        fail("HTML is missing local video player")
    if "data-time=" not in html:
        fail("HTML is missing timestamp jump controls")
    if "<iframe" in html.lower():
        fail("HTML must not embed iframe")
    if "bilibili.com" in html.lower():
        fail("local-jump output should not contain Bilibili links")
    if html.find("一句话总结") > html.find("时间线证据"):
        fail("summary should appear before evidence timeline")

    print("quick_validate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
