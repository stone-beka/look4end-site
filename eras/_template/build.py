#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""时代构建脚本模板：src/notes/*.md -> notes/*.html + notes/index.html + notes/doc.css"""
import os
import re
import shutil
import sys

try:
    import markdown
except ImportError:
    sys.exit("缺少 python-markdown，请先 pip install markdown")

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src", "notes")
OUT = os.path.join(ROOT, "notes")
SITE_NAME = "（改我：时代名）"

PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {site}</title>
<link rel="stylesheet" href="../era.css">
<link rel="stylesheet" href="doc.css">
</head>
<body class="doc">
<header class="doc__bar"><a href="../">← 本时代</a><a href="index.html">目录</a></header>
<article class="doc__body">
{body}
</article>
</body>
</html>
"""


def main():
    if not os.path.isdir(SRC):
        sys.exit("找不到 src/notes/")
    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT)
    pages = []
    for name in sorted(f for f in os.listdir(SRC) if f.endswith(".md")):
        with open(os.path.join(SRC, name), encoding="utf-8") as fh:
            raw = fh.read()
        md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc", "attr_list"])
        body = md.convert(raw)
        found = re.search(r"^#\s+(.+)$", raw, re.M)
        title = found.group(1).strip() if found else name[:-3]
        pages.append((name[:-3] + ".html", title, body))
    for filename, title, body in pages:
        with open(os.path.join(OUT, filename), "w", encoding="utf-8") as fh:
            fh.write(PAGE.format(title=title, site=SITE_NAME, body=body.rstrip()))
        print("  [OK] notes/%s" % filename)
    cards = "\n".join('<li><a href="%s">%s</a></li>' % (f, t) for f, t, _ in pages)
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(
            '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>%s · 笔记</title><link rel="stylesheet" href="../era.css">'
            '<link rel="stylesheet" href="doc.css"></head><body class="doc">'
            '<header class="doc__bar"><a href="../">← 本时代</a></header>'
            '<main class="doc__index"><h1>笔记</h1><ul>%s</ul></main></body></html>'
            % (SITE_NAME, cards)
        )
    shutil.copy2(os.path.join(SRC, "doc.css"), os.path.join(OUT, "doc.css"))
    print("  [OK] notes/index.html + notes/doc.css")


if __name__ == "__main__":
    main()
