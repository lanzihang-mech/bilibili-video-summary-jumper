#!/usr/bin/env python3
"""Render a learning-note Markdown summary into a timestamp-jump HTML page."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SEGMENT_RE = re.compile(
    r"###\s*<a id=\"t(?P<anchor>\d+)\"></a>(?P<label>.+?)\n"
    r"- time:\s*(?P<time>\d+)\n"
    r"- frame:\s*(?P<frame>.*)\n"
    r"- topic:\s*(?P<topic>.*)\n"
    r"- explanation:\s*(?P<explanation>.*)\n"
    r"- beginner_takeaway:\s*(?P<takeaway>.*)\n"
    r"- evidence:\s*(?P<evidence>.*)",
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


def plain_paragraph(text: str) -> str:
    return " ".join(line.strip() for line in text.splitlines() if line.strip() and not line.strip().startswith("- "))


def frame_uri(base_dir: Path, frame: str) -> str:
    frame_name = Path(frame).name
    return (base_dir / "frames" / frame_name).resolve().as_uri()


def parse_segments(markdown: str) -> list[dict[str, object]]:
    segments: list[dict[str, object]] = []
    for match in SEGMENT_RE.finditer(markdown):
        segments.append(
            {
                "seconds": int(match.group("time")),
                "label": match.group("label").strip(),
                "frame": match.group("frame").strip(),
                "topic": match.group("topic").strip(),
                "explanation": match.group("explanation").strip(),
                "takeaway": match.group("takeaway").strip(),
                "evidence": match.group("evidence").strip(),
            }
        )
    return segments


def render(markdown: str, source_url: str | None, local_video: str | None, base_dir: Path, title: str | None) -> str:
    page_title = title or markdown.splitlines()[0].lstrip("# ").strip() or "视频总结"
    one_sentence = plain_paragraph(section_text(markdown, "一句话总结"))
    audience = list_items(section_text(markdown, "适合谁看"))
    problem = plain_paragraph(section_text(markdown, "这段视频解决的问题"))
    key_points = list_items(section_text(markdown, "核心观点"))
    actions = list_items(section_text(markdown, "新手下一步行动"))
    segments = parse_segments(markdown)

    nav = []
    segment_cards = []
    evidence_cards = []
    for segment in segments:
        seconds = int(segment["seconds"])
        label = str(segment["label"])
        topic = str(segment["topic"])
        frame = str(segment["frame"])
        explanation = str(segment["explanation"])
        takeaway = str(segment["takeaway"])
        evidence = str(segment["evidence"])
        nav.append(f'<a href="#t{seconds}"><span>{html.escape(topic)}</span><span>{seconds}s</span></a>')
        image_html = ""
        if frame:
            image_html = f'<img src="{html.escape(frame_uri(base_dir, frame))}" alt="{html.escape(topic)}">'
        if local_video:
            action = f'<button class="jump" type="button" data-time="{seconds}">跳到这一段</button>'
        else:
            url = jump_url(source_url or "", seconds)
            action = f'<a class="jump" href="{html.escape(url)}" target="_blank" rel="noopener">跳到原视频</a>'
        segment_cards.append(
            f'<article class="learn-card" id="t{seconds}">'
            f'<div class="learn-text"><div class="time">{html.escape(label)}</div>'
            f'<h3>{html.escape(topic)}</h3>'
            f'<p>{html.escape(explanation)}</p>'
            f'<p class="takeaway"><strong>对新手：</strong>{html.escape(takeaway)}</p>'
            f'{action}</div>{image_html}</article>'
        )
        evidence_cards.append(
            f'<article class="evidence"><div><strong>{html.escape(label)}</strong><p>{html.escape(evidence)}</p></div>{action}</article>'
        )

    audience_html = "\n".join(f"<li>{html.escape(item)}</li>" for item in audience)
    points_html = "\n".join(f"<li>{html.escape(item)}</li>" for item in key_points)
    actions_html = "\n".join(f"<li>{html.escape(item)}</li>" for item in actions)

    video_panel = ""
    header_action = ""
    if local_video:
        video_src = html.escape(Path(local_video).resolve().as_uri())
        video_panel = f'<section class="player"><video id="localVideo" controls preload="metadata" src="{video_src}"></video></section>'
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
    :root {{ --ink:#17202a; --muted:#607080; --line:#d9e0e7; --paper:#f6f7f9; --panel:#fff; --accent:#0b6fcb; --accent-soft:#e7f1ff; --good:#13745d; --warn:#a46100; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,"Segoe UI","Microsoft YaHei",Arial,sans-serif; color:var(--ink); background:var(--paper); line-height:1.62; }}
    .shell {{ max-width:1160px; margin:0 auto; padding:28px 22px 46px; }}
    header {{ display:grid; grid-template-columns:minmax(0,1fr) auto; gap:20px; align-items:start; padding-bottom:20px; border-bottom:1px solid var(--line); }}
    h1 {{ margin:0 0 8px; font-size:34px; line-height:1.18; letter-spacing:0; }}
    .meta {{ color:var(--muted); font-size:14px; }}
    button {{ font:inherit; }}
    .source,.jump {{ display:inline-flex; align-items:center; justify-content:center; min-height:38px; padding:0 13px; border:0; border-radius:8px; text-decoration:none; font-weight:800; white-space:nowrap; cursor:pointer; }}
    .source {{ background:var(--accent); color:white; }}
    .jump {{ background:var(--accent-soft); color:#07599f; width:fit-content; }}
    main {{ display:grid; grid-template-columns:280px minmax(0,1fr); gap:22px; margin-top:24px; }}
    aside {{ position:sticky; top:18px; align-self:start; }}
    section {{ margin-bottom:24px; }}
    h2 {{ margin:0 0 12px; font-size:19px; letter-spacing:0; }}
    h3 {{ margin:3px 0 8px; font-size:20px; letter-spacing:0; }}
    p {{ margin:0; }}
    .panel,.learn-card,.evidence {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; }}
    .panel {{ padding:16px; }}
    .player video {{ width:100%; max-height:60vh; border-radius:8px; background:#101820; border:1px solid var(--line); }}
    .toc {{ display:grid; gap:8px; max-height:70vh; overflow:auto; padding-right:4px; }}
    .toc a {{ display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px; padding:9px 10px; border-radius:6px; text-decoration:none; background:#f1f4f7; color:var(--ink); font-size:14px; }}
    .lead {{ font-size:20px; font-weight:800; line-height:1.5; margin:0; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .compact-list {{ margin:0; padding-left:20px; }}
    .compact-list li {{ margin:6px 0; }}
    .problem {{ border-left:4px solid var(--warn); }}
    .segments {{ display:grid; gap:16px; }}
    .learn-card {{ display:grid; grid-template-columns:minmax(0,1fr) 280px; gap:16px; padding:16px; }}
    .learn-text {{ display:grid; gap:8px; align-content:start; }}
    .learn-card img {{ width:100%; border-radius:6px; border:1px solid var(--line); background:#eef1f4; }}
    .time {{ font-weight:900; color:var(--good); font-size:14px; }}
    .takeaway {{ background:#f8fafc; border-left:4px solid var(--good); padding:10px 12px; border-radius:6px; }}
    .evidence-list {{ display:grid; gap:10px; }}
    .evidence {{ display:grid; grid-template-columns:minmax(0,1fr) auto; gap:14px; align-items:center; padding:12px 14px; }}
    .evidence p {{ color:var(--muted); margin-top:4px; }}
    @media (max-width:860px) {{ header,main,.grid,.learn-card,.evidence {{ grid-template-columns:1fr; }} aside {{ position:static; }} h1 {{ font-size:28px; }} }}
  </style>
</head>
<body>
  <div class="shell">
    <header><div><h1>{html.escape(page_title)}</h1><div class="meta">本页由本地 MP4、ASR 字幕与截图证据生成；总结内容经过规则化改写，时间点可回到原片复核。</div></div>{header_action}</header>
    <main>
      <aside><section class="panel"><h2>时间导航</h2><nav class="toc">{''.join(nav)}</nav></section></aside>
      <div>
        {video_panel}
        <section class="panel"><h2>一句话总结</h2><p class="lead">{html.escape(one_sentence)}</p></section>
        <section class="grid">
          <div class="panel"><h2>适合谁看</h2><ul class="compact-list">{audience_html}</ul></div>
          <div class="panel problem"><h2>这段视频解决的问题</h2><p>{html.escape(problem)}</p></div>
        </section>
        <section class="panel"><h2>核心观点</h2><ul class="compact-list">{points_html}</ul></section>
        <section><h2>分段讲解</h2><div class="segments">{''.join(segment_cards)}</div></section>
        <section class="panel"><h2>新手下一步行动</h2><ul class="compact-list">{actions_html}</ul></section>
        <section><h2>时间线证据与跳转</h2><div class="evidence-list">{''.join(evidence_cards)}</div></section>
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
