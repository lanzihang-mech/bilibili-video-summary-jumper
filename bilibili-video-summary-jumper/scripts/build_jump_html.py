#!/usr/bin/env python3
"""Render a Markdown video summary into a timestamp-jump HTML page."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TIMELINE_RE = re.compile(
    r"###\s*<a id=\"t(?P<anchor>\d+)\"></a>(?P<label>.+?)\n"
    r"- time:\s*(?P<time>\d+)\n"
    r"- frame:\s*(?P<frame>.*)\n"
    r"- summary:\s*(?P<summary>.*)",
    re.MULTILINE,
)


def jump_url(source_url: str, seconds: int) -> str:
    split = urlsplit(source_url)
    query = dict(parse_qsl(split.query, keep_blank_values=True))
    query["t"] = str(max(0, seconds))
    return urlunsplit((split.scheme, split.netloc, split.path, urlencode(query), split.fragment))


def section_text(markdown: str, heading: str) -> str:
    pattern = re.compile(rf"## {re.escape(heading)}\n(?P<body>.*?)(?=\n## |\Z)", re.S)
    match = pattern.search(markdown)
    return match.group("body").strip() if match else ""


def list_items(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:])
    return items


def render(markdown: str, source_url: str | None, local_video: str | None, base_dir: Path, title: str | None) -> str:
    page_title = title or markdown.splitlines()[0].lstrip("# ").strip() or "视频总结"
    overview = list_items(section_text(markdown, "总览"))
    key_points = list_items(section_text(markdown, "关键观点"))
    citations = list_items(section_text(markdown, "可复用引用"))
    cards = []
    nav = []
    for match in TIMELINE_RE.finditer(markdown):
        seconds = int(match.group("time"))
        label = match.group("label").strip()
        frame = match.group("frame").strip()
        summary = match.group("summary").strip()
        url = jump_url(source_url, seconds) if source_url else ""
        nav.append(f'<a href="#t{seconds}"><span>{html.escape(label)}</span><span>{seconds}s</span></a>')
        image_html = ""
        if frame:
            frame_path = (base_dir / "frames" / frame).resolve()
            image_html = f'<img src="{html.escape(frame_path.as_uri())}" alt="{html.escape(label)}">'
        if local_video:
            action = f'<button class="jump" type="button" data-time="{seconds}">跳转本地视频</button>'
        else:
            action = f'<a class="jump" href="{html.escape(url)}" target="_blank" rel="noopener">跳转到原视频</a>'
        cards.append(
            f'<article class="card" id="t{seconds}">{image_html}<div class="card-body">'
            f'<div class="time">{html.escape(label)}</div><p>{html.escape(summary)}</p>'
            f'{action}'
            '</div></article>'
        )
    overview_html = "\n".join(f"<li>{html.escape(item)}</li>" for item in overview)
    points_html = "\n".join(f'<article class="point">{html.escape(item)}</article>' for item in key_points)
    citation_html = html.escape("\n".join(citations))
    video_panel = ""
    header_action = ""
    if local_video:
        video_src = html.escape(Path(local_video).resolve().as_uri())
        video_panel = f'<section class="panel player"><h2>本地视频</h2><video id="localVideo" controls preload="metadata" src="{video_src}"></video></section>'
        header_action = '<button class="source" type="button" data-time="0">从头播放</button>'
    elif source_url:
        header_action = f'<a class="source" href="{html.escape(source_url)}" target="_blank" rel="noopener">打开原视频</a>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(page_title)}</title>
  <style>
    :root {{ --ink:#17202a; --muted:#5f6e7a; --line:#d8dee6; --paper:#f7f8fa; --panel:#fff; --accent:#0a7cff; --good:#147d64; --mark:#f0b429; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,"Segoe UI","Microsoft YaHei",Arial,sans-serif; color:var(--ink); background:var(--paper); line-height:1.55; }}
    .shell {{ max-width:1180px; margin:0 auto; padding:28px 22px 44px; }}
    header {{ display:grid; grid-template-columns:minmax(0,1fr) auto; gap:20px; align-items:start; padding-bottom:22px; border-bottom:1px solid var(--line); }}
    h1 {{ margin:0 0 10px; font-size:clamp(28px,4vw,46px); line-height:1.12; letter-spacing:0; }}
    .meta {{ color:var(--muted); font-size:14px; }}
    button {{ font: inherit; }}
    .source,.jump {{ display:inline-flex; align-items:center; justify-content:center; min-height:38px; padding:0 12px; border:0; border-radius:8px; text-decoration:none; font-weight:800; white-space:nowrap; cursor:pointer; }}
    .source {{ background:var(--accent); color:white; }}
    .jump {{ background:#e8f2ff; color:#075bbb; width:fit-content; }}
    main {{ display:grid; grid-template-columns:300px minmax(0,1fr); gap:22px; margin-top:24px; }}
    aside {{ position:sticky; top:18px; align-self:start; }}
    section {{ margin-bottom:24px; }}
    h2 {{ margin:0 0 12px; font-size:18px; letter-spacing:0; }}
    .panel,.point,.card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; }}
    .panel {{ padding:16px; }}
    .player video {{ width:100%; max-height:62vh; border-radius:8px; background:#101820; }}
    .toc {{ display:grid; gap:8px; max-height:70vh; overflow:auto; padding-right:4px; }}
    .toc a {{ display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px; padding:9px 10px; border-radius:6px; text-decoration:none; background:#f3f6f8; color:var(--ink); font-size:14px; }}
    .overview {{ display:grid; gap:10px; margin:0; padding-left:18px; }}
    .points {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
    .point {{ border-left:4px solid var(--mark); padding:12px 14px; }}
    .timeline {{ display:grid; gap:14px; }}
    .card {{ display:grid; grid-template-columns:260px minmax(0,1fr); gap:14px; padding:14px; }}
    .card img {{ width:100%; border-radius:6px; border:1px solid var(--line); background:#eef1f4; }}
    .card-body {{ display:grid; gap:8px; align-content:start; }}
    .time {{ font-weight:900; color:var(--good); }}
    .card p {{ margin:0; color:var(--ink); }}
    .citation {{ width:100%; min-height:160px; resize:vertical; border:1px solid var(--line); border-radius:8px; padding:12px; font:13px/1.5 Consolas,monospace; }}
    @media (max-width:860px) {{ header,main,.card {{ grid-template-columns:1fr; }} aside {{ position:static; }} .points {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <div class="shell">
    <header><div><h1>{html.escape(page_title)}</h1><div class="meta">本页由本地 MP4、ASR 字幕与截图证据生成</div></div>{header_action}</header>
    <main>
      <aside><section class="panel"><h2>章节导航</h2><nav class="toc">{''.join(nav)}</nav></section></aside>
      <div>
        {video_panel}
        <section class="panel"><h2>总览</h2><ol class="overview">{overview_html}</ol></section>
        <section><h2>关键观点</h2><div class="points">{points_html}</div></section>
        <section><h2>时间线证据</h2><div class="timeline">{''.join(cards)}</div></section>
        <section class="panel"><h2>可复用引用</h2><textarea class="citation" readonly>{citation_html}</textarea></section>
      </div>
    </main>
  </div>
  <script>
    const video = document.getElementById('localVideo');
    document.querySelectorAll('[data-time]').forEach((button) => {{
      button.addEventListener('click', () => {{
        const target = Number(button.dataset.time || 0);
        if (video) {{
          video.currentTime = target;
          video.play();
          video.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
      }});
    }});
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render jumpable HTML from video summary Markdown.")
    parser.add_argument("markdown")
    parser.add_argument("--source-url", default=None)
    parser.add_argument("--local-video", default=None)
    parser.add_argument("--output", default="video-summary.html")
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    md_path = Path(args.markdown)
    markdown = md_path.read_text(encoding="utf-8")
    if not args.source_url and not args.local_video:
        raise SystemExit("Provide either --local-video or --source-url.")
    html_output = render(markdown, args.source_url, args.local_video, md_path.parent, args.title)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html_output, encoding="utf-8")
    print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
