#!/usr/bin/env python3
"""Fetch Bilibili subtitles with yt-dlp without downloading video media."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, text=True, capture_output=True, encoding="utf-8", errors="replace")


def find_yt_dlp(explicit_path: str | None) -> str | None:
    if explicit_path:
        candidate = Path(explicit_path)
        if candidate.exists():
            return str(candidate)
        return explicit_path
    return shutil.which("yt-dlp")


def choose_subtitle_file(output_dir: Path) -> Path | None:
    files = [p for p in output_dir.glob("*") if p.suffix.lower() in {".srt", ".vtt"}]
    if not files:
        return None

    def score(path: Path) -> tuple[int, int]:
        name = path.name.lower()
        lang_score = 0
        for needle, value in (
            ("zh-hans", 80),
            ("zh_cn", 75),
            ("zh-cn", 75),
            (".zh.", 70),
            ("chinese", 65),
            ("en", 30),
        ):
            if needle in name:
                lang_score = max(lang_score, value)
        suffix_score = 10 if path.suffix.lower() == ".vtt" else 8
        return lang_score + suffix_score, path.stat().st_size

    return sorted(files, key=score, reverse=True)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Bilibili subtitles through yt-dlp.")
    parser.add_argument("url", help="Bilibili video URL")
    parser.add_argument("--output-dir", default="out", help="Directory for subtitle files")
    parser.add_argument("--yt-dlp", default=None, help="Path to yt-dlp executable")
    parser.add_argument("--cookies", default=None, help="Optional cookies file for Bilibili login-protected subtitles")
    args = parser.parse_args()

    yt_dlp = find_yt_dlp(args.yt_dlp)
    if not yt_dlp:
        print(
            "ERROR: yt-dlp was not found. Install yt-dlp or pass --yt-dlp PATH.\n"
            "Fallback: copy SRT/VTT with vCaptions or bili-subtitle-copier, then run build_summary_html.py.",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    list_cmd = [yt_dlp, "--no-playlist", "--list-subs", args.url]
    if args.cookies:
        list_cmd[1:1] = ["--cookies", args.cookies]
    list_result = run_command(list_cmd)

    download_cmd = [
        yt_dlp,
        "--no-playlist",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "all,-danmaku",
        "--sub-format",
        "vtt/srt",
        "--output",
        str(output_dir / "%(id)s.%(ext)s"),
        args.url,
    ]
    if args.cookies:
        download_cmd[1:1] = ["--cookies", args.cookies]

    download_result = run_command(download_cmd)
    subtitle_file = choose_subtitle_file(output_dir)
    manifest = {
        "url": args.url,
        "subtitle_file": str(subtitle_file) if subtitle_file else None,
        "list_subs_exit_code": list_result.returncode,
        "download_exit_code": download_result.returncode,
        "list_subs_output": list_result.stdout[-4000:],
        "download_output": (download_result.stdout + download_result.stderr)[-4000:],
    }
    (output_dir / "subtitle_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if not subtitle_file:
        print(
            "ERROR: no subtitle file was downloaded.\n"
            "Fallback: copy SRT/VTT with vCaptions or bili-subtitle-copier, save it as a file, then run build_summary_html.py.",
            file=sys.stderr,
        )
        if list_result.stdout:
            print("\n--- yt-dlp --list-subs output ---\n" + list_result.stdout, file=sys.stderr)
        if download_result.stderr:
            print("\n--- yt-dlp download stderr ---\n" + download_result.stderr, file=sys.stderr)
        return 3

    print(str(subtitle_file))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
