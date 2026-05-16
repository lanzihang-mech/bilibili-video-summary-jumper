#!/usr/bin/env python3
"""Fetch Bilibili subtitles with yt-dlp without downloading video media."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def extract_bvid(url_or_bvid: str) -> str | None:
    match = re.search(r"BV[a-zA-Z0-9]+", url_or_bvid)
    return match.group(0) if match else None


def request_json(url: str, referer: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": referer,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def format_srt_time(seconds: float) -> str:
    total_ms = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def write_bilibili_json_as_srt(subtitle_json: dict, output_path: Path) -> None:
    body = subtitle_json.get("body") or []
    lines: list[str] = []
    for index, item in enumerate(body, start=1):
        start = float(item.get("from", 0))
        end = float(item.get("to", start + 1))
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        lines.extend(
            [
                str(index),
                f"{format_srt_time(start)} --> {format_srt_time(max(end, start + 0.5))}",
                content,
                "",
            ]
        )
    output_path.write_text("\n".join(lines), encoding="utf-8")


def fetch_public_subtitle(url: str, output_dir: Path, page: int | None) -> Path | None:
    bvid = extract_bvid(url)
    if not bvid:
        return None
    view = request_json(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}", url)
    if view.get("code") != 0:
        return None
    pages = view.get("data", {}).get("pages") or []
    selected_page = page or int(dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)).get("p", "1") or "1")
    cid = None
    for item in pages:
        if int(item.get("page", 0)) == selected_page:
            cid = item.get("cid")
            break
    cid = cid or view.get("data", {}).get("cid")
    if not cid:
        return None
    player = request_json(f"https://api.bilibili.com/x/player/v2?bvid={bvid}&cid={cid}", url)
    subtitles = player.get("data", {}).get("subtitle", {}).get("subtitles") or []
    if not subtitles:
        return None

    def subtitle_score(item: dict) -> int:
        lan = str(item.get("lan", "")).lower()
        lan_doc = str(item.get("lan_doc", "")).lower()
        value = 0
        for needle, score in (("zh", 80), ("chinese", 70), ("ai", 15), ("en", 20)):
            if needle in lan or needle in lan_doc:
                value = max(value, score)
        return value

    selected = sorted(subtitles, key=subtitle_score, reverse=True)[0]
    subtitle_url = selected.get("subtitle_url") or selected.get("url")
    if not subtitle_url:
        return None
    if subtitle_url.startswith("//"):
        subtitle_url = "https:" + subtitle_url
    subtitle_json = request_json(str(subtitle_url), url)
    output_path = output_dir / f"{bvid}.p{selected_page}.bilibili.srt"
    write_bilibili_json_as_srt(subtitle_json, output_path)
    return output_path if output_path.exists() and output_path.stat().st_size > 0 else None


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
    parser.add_argument("--page", type=int, default=None, help="Optional multi-part page number")
    parser.add_argument("--skip-public-api", action="store_true", help="Skip Bilibili public subtitle API check")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    public_api_error = None
    if not args.skip_public_api:
        try:
            subtitle_file = fetch_public_subtitle(args.url, output_dir, args.page)
            if subtitle_file:
                print(str(subtitle_file))
                return 0
        except Exception as exc:
            public_api_error = str(exc)

    yt_dlp = find_yt_dlp(args.yt_dlp)
    if not yt_dlp:
        print(
            "ERROR: no public Bilibili subtitle was found and yt-dlp was not found. Install yt-dlp or pass --yt-dlp PATH.\n"
            "Fallback: copy SRT/VTT with vCaptions or bili-subtitle-copier, or run transcribe_bili_asr.py for local ASR.",
            file=sys.stderr,
        )
        return 2

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
        "public_api_error": public_api_error,
        "list_subs_exit_code": list_result.returncode,
        "download_exit_code": download_result.returncode,
        "list_subs_output": list_result.stdout[-4000:],
        "download_output": (download_result.stdout + download_result.stderr)[-4000:],
    }
    (output_dir / "subtitle_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    if not subtitle_file:
        print(
            "ERROR: no subtitle file was downloaded.\n"
            "Fallback: copy SRT/VTT with vCaptions or bili-subtitle-copier, or run transcribe_bili_asr.py for local ASR.",
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
