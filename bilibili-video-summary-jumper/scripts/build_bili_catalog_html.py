#!/usr/bin/env python3
"""Build a Bilibili multi-part catalog summary HTML from public video metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def extract_bvid(url_or_bvid: str) -> str:
    match = re.search(r"BV[a-zA-Z0-9]+", url_or_bvid)
    if not match:
        raise SystemExit("No BV id found in URL.")
    return match.group(0)


def format_time(seconds: int) -> str:
    hours, rem = divmod(max(0, int(seconds)), 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def jump_url(bvid: str, page: int) -> str:
    return f"https://www.bilibili.com/video/{bvid}/?p={page}&t=0"


def classify(part: str) -> str:
    if any(word in part for word in ("安装", "PyCharm", "项目", "开始")):
        return "环境准备"
    if any(word in part for word in ("print", "变量", "命名", "数学", "注释", "数据类型", "input", "交互")):
        return "基础语法"
    if any(word in part for word in ("条件", "循环", "列表", "元组", "字典", "字符串")):
        return "控制流与数据结构"
    if any(word in part for word in ("函数", "模块", "匿名", "高阶")):
        return "函数与模块"
    if any(word in part for word in ("对象", "类", "继承")):
        return "面向对象"
    if any(word in part for word in ("文件", "异常", "测试", "bug")):
        return "工程实践"
    return "导入与收束"


def render(data: dict, bvid: str) -> str:
    video = data["data"]
    pages = video["pages"]
    groups: dict[str, list[dict]] = {}
    for page in pages:
        groups.setdefault(classify(page["part"]), []).append(page)

    nav = []
    cards = []
    citation = []
    total = 0
    for page in pages:
        total += int(page["duration"])
        url = jump_url(bvid, int(page["page"]))
        part = html.escape(page["part"])
        duration = format_time(int(page["duration"]))
        nav.append(f'<a href="#p{page["page"]}"><span>P{page["page"]:02d}</span><span>{duration}</span></a>')
        cards.append(
            f'<article class="card" id="p{page["page"]}">'
            f'<div class="time">P{page["page"]:02d}<small>{duration}</small></div>'
            f'<div><strong>{part}</strong><p>{html.escape(classify(page["part"]))}</p></div>'
            f'<a class="jump" href="{html.escape(url)}" target="_blank" rel="noopener">跳转</a>'
            "</article>"
        )
        citation.append(f'P{page["page"]:02d} {page["part"]} {url}')

    points = []
    for name, items in groups.items():
        total_duration = sum(int(item["duration"]) for item in items)
        first = items[0]
        points.append(
            f'<article class="point"><strong>{html.escape(name)}</strong>'
            f'<p>{len(items)} 节，约 {format_time(total_duration)}。从 P{first["page"]:02d}「{html.escape(first["part"])}」开始。</p></article>'
        )

    overview_items = [
        f'这是一个 {len(pages)}P 的 Python 零基础入门合集，总时长约 {format_time(total)}。',
        '课程路线从安装 Python/PyCharm 和创建项目开始，再进入 print、变量、数据类型、输入输出等基础语法。',
        '中段覆盖条件判断、循环、列表、元组、字典等编程基础，再过渡到函数、模块、面向对象。',
        '后段补上文件操作、异常处理、测试、高阶函数等工程实践主题，适合作为一条完整入门路线。',
        '当前页面基于 B 站公开视频分 P 元数据生成；若后续提供字幕，可升级为逐时间戳证据版总结。',
    ]
    overview = "\n".join(f"<li>{html.escape(item)}</li>" for item in overview_items)

    title = html.escape(video["title"])
    owner = html.escape(video["owner"]["name"])
    desc = html.escape(video.get("desc", ""))
    source_url = f"https://www.bilibili.com/video/{bvid}/"
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{ --ink:#17202a; --muted:#61707f; --line:#d8dee6; --paper:#f7f8fa; --panel:#fff; --accent:#0a7cff; --good:#147d64; --mark:#f0b429; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family:Inter,"Segoe UI","Microsoft YaHei",Arial,sans-serif; color:var(--ink); background:var(--paper); line-height:1.55; }}
    .shell {{ max-width:1180px; margin:0 auto; padding:28px 22px 44px; }}
    header {{ display:grid; grid-template-columns:minmax(0,1fr) auto; gap:20px; align-items:start; padding-bottom:22px; border-bottom:1px solid var(--line); }}
    h1 {{ margin:0 0 10px; font-size:clamp(26px,4vw,44px); line-height:1.12; letter-spacing:0; }}
    .meta {{ color:var(--muted); display:flex; flex-wrap:wrap; gap:8px 14px; font-size:14px; }}
    .source,.jump {{ display:inline-flex; align-items:center; justify-content:center; min-height:38px; padding:0 12px; border-radius:8px; text-decoration:none; font-weight:800; white-space:nowrap; }}
    .source {{ background:var(--accent); color:white; }}
    .jump {{ background:#e8f2ff; color:#075bbb; }}
    main {{ display:grid; grid-template-columns:300px minmax(0,1fr); gap:22px; margin-top:24px; }}
    aside {{ position:sticky; top:18px; align-self:start; }}
    section {{ margin-bottom:24px; }}
    h2 {{ margin:0 0 12px; font-size:18px; letter-spacing:0; }}
    .panel,.card,.point {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; }}
    .panel {{ padding:16px; }}
    .toc {{ display:grid; gap:8px; max-height:70vh; overflow:auto; padding-right:4px; }}
    .toc a {{ display:flex; justify-content:space-between; gap:10px; padding:9px 10px; border-radius:6px; text-decoration:none; background:#f3f6f8; color:var(--ink); font-size:14px; }}
    .overview {{ display:grid; gap:10px; margin:0; padding-left:18px; }}
    .desc {{ color:var(--muted); white-space:pre-wrap; }}
    .points {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
    .point {{ border-left:4px solid var(--mark); padding:12px 14px; min-height:92px; }}
    .point p,.card p {{ margin:6px 0 0; color:var(--muted); }}
    .timeline {{ display:grid; gap:12px; }}
    .card {{ padding:14px; display:grid; grid-template-columns:86px minmax(0,1fr) auto; gap:14px; align-items:start; }}
    .time {{ font-weight:900; color:var(--good); }}
    .time small {{ display:block; color:var(--muted); font-weight:600; margin-top:3px; }}
    .citation {{ width:100%; min-height:180px; resize:vertical; border:1px solid var(--line); border-radius:8px; padding:12px; font:13px/1.5 Consolas,monospace; color:var(--ink); background:#fbfcfd; }}
    @media (max-width:860px) {{ header,main {{ grid-template-columns:1fr; }} aside {{ position:static; }} .points {{ grid-template-columns:1fr; }} .card {{ grid-template-columns:1fr; }} .source,.jump {{ width:fit-content; }} }}
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <div>
        <h1>{title}</h1>
        <div class="meta"><span>UP：{owner}</span><span>分 P：{len(pages)}</span><span>总时长：{format_time(total)}</span><span>生成时间：{dt.datetime.now().strftime("%Y-%m-%d %H:%M")}</span></div>
      </div>
      <a class="source" href="{source_url}" target="_blank" rel="noopener">打开原视频</a>
    </header>
    <main>
      <aside><section class="panel"><h2>分 P 导航</h2><nav class="toc">{''.join(nav)}</nav></section></aside>
      <div>
        <section class="panel"><h2>总览</h2><ol class="overview">{overview}</ol></section>
        <section class="panel"><h2>视频简介</h2><p class="desc">{desc}</p></section>
        <section><h2>学习模块</h2><div class="points">{''.join(points)}</div></section>
        <section><h2>分 P 跳转目录</h2><div class="timeline">{''.join(cards)}</div></section>
        <section class="panel"><h2>可复制引用</h2><textarea class="citation" readonly>{html.escape(chr(10).join(citation))}</textarea></section>
      </div>
    </main>
  </div>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Bilibili catalog summary HTML.")
    parser.add_argument("url", help="Bilibili video URL")
    parser.add_argument("--output", default="catalog-summary.html")
    parser.add_argument("--metadata-json", default=None)
    args = parser.parse_args()
    bvid = extract_bvid(args.url)
    data = fetch_json(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
    if data.get("code") != 0:
        raise SystemExit(f"Bilibili API error: {data}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render(data, bvid), encoding="utf-8")
    metadata = Path(args.metadata_json) if args.metadata_json else output.with_suffix(".metadata.json")
    metadata.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(output))
    print(str(metadata))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
