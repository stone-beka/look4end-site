#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py —— 把「构成主义动效（视频）」这组文档构建成站点页面

产物直接写进发布仓库的 motion/（= 站点上的「视频设计」层级）：

    look4end-site/motion/
      index.html                    ← 动效原型（别人维护，本脚本【不碰】）
      README.html                   ← 本组文档总览
      01-动效设计理念.html
      02-视频制作·结构主义经验.html

样式复用 notes/ 里那一套（kv.css + doc.css），不重复一份：
    页面里链接写作 ../notes/kit/kv.css 与 ../notes/doc.css

链接改写：源文档里的相对路径（../constructivism/、../../constructivism-motion-20s.html、
../../tools/...）在站点上都不存在，必须映射或降级，否则上线即 404。
"""
import os
import re
import sys

try:
    import markdown
except ImportError:
    sys.exit("缺少 python-markdown，请先 pip install markdown")

SRC = os.path.dirname(os.path.abspath(__file__))


def default_out(section="motion"):
    """产物目录自动判定，让同一份脚本在本机源项目和仓库里都能直接用：

    - 脚本在仓库的 src/<section>/ 下（上两层有 index.html 和 notes/）→ 写仓库的 <section>/
    - 否则 → 写同级的 上线/

    本机源项目不在仓库结构里时，用 --out 显式指定。
    """
    repo = os.path.abspath(os.path.join(SRC, "..", ".."))
    if os.path.isfile(os.path.join(repo, "index.html")) and os.path.isdir(os.path.join(repo, "notes")):
        return os.path.join(repo, section)
    return os.path.join(SRC, "上线")


OUT = default_out()

MD_EXT = ["tables", "fenced_code", "sane_lists", "toc", "attr_list"]

# 页面顺序：总览在前，再 01 / 02
PAGES = ["README", "01-动效设计理念", "02-视频制作·结构主义经验"]

# 源文档里的路径 → 站点上的真实地址
LINK_MAP = {
    "../../constructivism-motion-20s.html": "index.html",      # 动效原型
    "../../constructivism-motion-20s-v2.html": "index.html",   # 同一原型的另一版，站点上只有一份
    "../constructivism/README.md": "../notes/README.html",
    "../constructivism/01-美学谱系与形式法则.md": "../notes/01-美学谱系与形式法则.html",
    "../constructivism/02-设计系统规格.md": "../notes/02-设计系统规格.html",
    "../constructivism/": "../notes/",
    # 未上线的源码/脚本：降级成纯文字，不留死链
    "../../tools/render-frames.cjs": None,
}

NOT_PUBLISHED_PREFIX = ("../../tools/", "../../.scratch/")


def md_to_html(text):
    md = markdown.Markdown(extensions=MD_EXT,
                           extension_configs={"toc": {"permalink": False, "toc_depth": "2-3"}})
    html = md.convert(text)
    html = html.replace("<table>", '<div class="table-wrap"><table>')
    html = html.replace("</table>", "</table></div>")

    def add_link(m):
        tag, hid, inner = m.group(1), m.group(2), m.group(3)
        return '<%s id="%s">%s<a class="headerlink" href="#%s" aria-hidden="true">#</a></%s>' % (
            tag, hid, inner, hid, tag)
    return re.sub(r'<(h[23]) id="([^"]+)">(.*?)</\1>', add_link, html, flags=re.S)


def rewrite_links(text):
    """返回 (新文本, 降级条数, 站外链接)"""
    unlinked = [0]
    outside = []

    def repl(m):
        label, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)

        if target in LINK_MAP:
            mapped = LINK_MAP[target]
            if mapped is None:
                unlinked[0] += 1
                return label                      # 未上线 → 纯文字
            return "[%s](%s)" % (label, mapped)

        t, _, frag = target.partition("#")
        # 走到这里说明既不在映射表里、也不是站内 .md —— 才是真正需要人工看的站外链接
        if t.startswith("../../"):
            outside.append(target)
        if any(t.startswith(p) for p in NOT_PUBLISHED_PREFIX):
            unlinked[0] += 1
            return label
        if t.endswith(".md"):
            new = t[:-3] + ".html" + (("#" + frag) if frag else "")
            return "[%s](%s)" % (label, new)
        return m.group(0)

    return re.sub(r"\[([^\]]*)\]\(([^)\s]+)\)", repl, text), unlinked[0], outside


def first_h1(text, fallback):
    m = re.search(r"^#\s+(.+)$", text, flags=re.M)
    if not m:
        return fallback
    return re.sub(r"^\d+\s*[·.\-]\s*", "", m.group(1).strip())


PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · 视频设计</title>
<meta name="description" content="{title}">
<link rel="stylesheet" href="../notes/kit/kv.css">
<link rel="stylesheet" href="../notes/doc.css">
</head>
<body>

<div class="kv-axis" aria-hidden="true"></div>

<div class="doc">
  <header class="doc__top">
    <a class="doc__back" href="README.html">← 视频设计</a>
    <span class="doc__no">{no}</span>
  </header>

  <article class="doc__body">
{body}
  </article>

  <nav class="doc__nav" aria-label="翻页">
    {prev}
    <a href="index.html">动效原型</a>
    <a href="../">站点首页</a>
    {next}
  </nav>
</div>

</body>
</html>
"""


def build():
    os.makedirs(OUT, exist_ok=True)
    warn, outside_all, unlinked_total = [], [], 0
    total = len(PAGES)

    for i, name in enumerate(PAGES, 1):
        src = os.path.join(SRC, name + ".md")
        if not os.path.exists(src):
            warn.append("缺源文件：%s.md" % name)
            continue
        with open(src, encoding="utf-8") as f:
            raw = f.read()

        # 自检：围栏代码块必须成对，否则后半篇会被整个吞成代码块
        n_fence = len(re.findall(r"(?m)^\s*```", raw))
        if n_fence % 2:
            warn.append("%s：``` 出现 %d 次（奇数，没闭合）" % (name, n_fence))

        raw2, n_unlinked, outside = rewrite_links(raw)
        unlinked_total += n_unlinked
        outside_all += ["%s → %s" % (name, o) for o in outside]

        body = md_to_html(raw2)

        raw_nocode = re.sub(r"(?ms)^\s*```.*?^\s*```\s*$", "", raw2)
        n_src_h = len(re.findall(r"(?m)^#{1,4}\s", raw_nocode))
        n_out_h = len(re.findall(r"<h[1-4][\s>]", body))
        if n_out_h < n_src_h:
            warn.append("%s：源 %d 个标题，产物只解析出 %d 个" % (name, n_src_h, n_out_h))

        title = first_h1(raw, name)
        prev_a = ('<a href="%s.html">← %s</a>' % (PAGES[i - 2], PAGES[i - 2]) if i > 1 else "<span></span>")
        next_a = ('<a href="%s.html">%s →</a>' % (PAGES[i], PAGES[i]) if i < total else "<span></span>")

        out = PAGE.format(title=title, no="%02d / %02d" % (i, total),
                          body=body.rstrip(), prev=prev_a, next=next_a)
        dst = os.path.join(OUT, name + ".html")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(out)
        print("  [OK] motion/%-30s %6.1f KB" % (name + ".html", os.path.getsize(dst) / 1024))

    if unlinked_total:
        print("\n  已把 %d 条指向未上线文件的链接降级成纯文字" % unlinked_total)
    if outside_all:
        print("\n  ⚠️ 仍指向站外的链接：")
        for o in outside_all:
            print("     " + o)
    if warn:
        print("\n  ⚠️ 自检告警：")
        for w in warn:
            print("     " + w)
    print("\n  motion/index.html（动效原型）本脚本不碰。")
    print("  共 %d 篇 → %s" % (total, OUT))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="把视频设计文档 .md 构建成站点页面")
    ap.add_argument("--out", default=OUT,
                    help="产物目录。默认自动判定：在仓库 src/motion/ 下就写 ../../motion/，否则写 ./上线/")
    args = ap.parse_args()
    OUT = os.path.abspath(args.out)
    print("构建视频设计文档：")
    build()
