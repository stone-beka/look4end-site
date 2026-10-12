#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build.py —— 把本目录的 Markdown 文档构建成「只含网页文件」的上线目录

产出结构（上线时把这个目录整体传上去即可）：

    上线/
      index.html            站点首页
      01-…html … README.html  各篇文档
      doc.css               文章版面
      kit/index.html        样式指南
      kit/kv.css            设计系统（含 Google Fonts 依赖，见下）

**上线目录里只有 .html 和 .css** —— 不含 .md 源、不含 verify/ 脚本、不含本脚本。

来源与产物分开放：
    结构主义html/          ← 工作目录：.md 源 / build.py / verify/ / kit/（源）
    结构主义html/上线/      ← 上线目录：只有网页文件

⚠️ 已知依赖：kit/kv.css 第 14 行 @import 了 Google Fonts。
   读者断网、或在大陆网络环境下，会退化成系统字体（版面不塌，但构成主义的窄体/黑体特征会失去）。
   这一条是照原设计保留的，没有擅自改。要改见 README 的说明。
"""
import os
import re
import shutil
import sys

try:
    import markdown
except ImportError:
    sys.exit("缺少 python-markdown，请先 pip install markdown")

ROOT = os.path.dirname(os.path.abspath(__file__))


def default_out(section="notes"):
    """产物目录自动判定，好让同一份脚本在本机源项目和仓库里都能直接用：

    - 脚本在仓库的 src/<section>/ 下（上一层的上一层有 index.html 和 notes/）
      → 产物写到仓库的 <section>/
    - 否则（本机源项目）→ 产物写到同级的 上线/

    也可以用 --out 显式指定。
    """
    repo = os.path.abspath(os.path.join(ROOT, "..", ".."))
    if os.path.isfile(os.path.join(repo, "index.html")) and os.path.isdir(os.path.join(repo, "notes")):
        return os.path.join(repo, section)
    return os.path.join(ROOT, "上线")


OUT = default_out()

SITE_TITLE = "构成主义 · HTML 设计美学经验"
SITE_SUB = "9 条形式法则 / 设计系统 / 交互模式 / 踩坑清单"

MD_EXT = ["tables", "fenced_code", "sane_lists", "toc", "attr_list"]


def collect_pages():
    """返回上线页面的文件名列表；README 放最后当「总览」"""
    files = [f for f in os.listdir(ROOT) if f.endswith(".md")]
    numbered = sorted(f for f in files if re.match(r"^\d\d-", f))
    others = sorted(f for f in files if not re.match(r"^\d\d-", f))
    return [f[:-3] + ".html" for f in numbered + others]


def md_to_html(md_text):
    md = markdown.Markdown(extensions=MD_EXT, extension_configs={
        "toc": {"permalink": False, "toc_depth": "2-3"},
    })
    html = md.convert(md_text)

    # 表格包一层，窄屏可横向滚动
    html = html.replace("<table>", '<div class="table-wrap"><table>')
    html = html.replace("</table>", "</table></div>")

    # 给 h2/h3 加锚点链接（样式在 doc.css 里）
    def add_link(m):
        tag, hid, inner = m.group(1), m.group(2), m.group(3)
        return '<%s id="%s">%s<a class="headerlink" href="#%s" aria-hidden="true">#</a></%s>' % (
            tag, hid, inner, hid, tag)

    return re.sub(r'<(h[23]) id="([^"]+)">(.*?)</\1>', add_link, html, flags=re.S)


# 不会上线的路径。正文里链到它们时，把链接降级成纯文字 —— 否则线上是 404。
NOT_PUBLISHED = ("verify/", "build.py", "_shot/", "上线/", "__pycache__/")


def rewrite_links(text):
    """改写链接：.md→.html；指向未上线路径的降级成纯文字
    返回 (新文本, 站外链接, 改写条数, 降级条数)

    ⚠️ 必须重建整条链接 "[标签](目标)"，不能只返回 "(目标)"。
    正则匹配掉的包含 "]( " 两个字符，少还一个 ] 就会把 "](url)" 变成 "(url)"，
    Markdown 链接全部失效 —— 而且失效后产物里再也找不到 "]( "，
    于是"检查有没有残留 ]( "这类自检反而会报通过。这个坑踩过一次，别再踩。
    """
    outside = []
    count = [0]
    unlinked = [0]

    def repl(m):
        label, target = m.group(1), m.group(2)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)
        if target.startswith("../"):
            outside.append(target)

        t, _, frag = target.partition("#")
        t_norm = t[2:] if t.startswith("./") else t      # ./verify/ → verify/
        if any(t_norm == p.rstrip("/") or t_norm.startswith(p) for p in NOT_PUBLISHED):
            unlinked[0] += 1
            return label                      # 降级成纯文字，不留死链
        if t.endswith(".md"):
            count[0] += 1
            new = t[:-3] + ".html" + (("#" + frag) if frag else "")
            return "[%s](%s)" % (label, new)
        return m.group(0)

    return re.sub(r"\[([^\]]*)\]\(([^)\s]+)\)", repl, text), outside, count[0], unlinked[0]


def first_h1(md_text, fallback):
    m = re.search(r"^#\s+(.+)$", md_text, flags=re.M)
    if not m:
        return fallback
    return re.sub(r"^\d+\s*[·.\-]\s*", "", m.group(1).strip())


PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · {site}</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="kit/kv.css">
<link rel="stylesheet" href="doc.css">
</head>
<body>

<div class="kv-axis" aria-hidden="true"></div>

<div class="doc">
  <header class="doc__top">
    <a class="doc__back" href="index.html">← 目录</a>
    <span class="doc__no">{no}</span>
  </header>

  <article class="doc__body">
{body}
  </article>

  <nav class="doc__nav" aria-label="翻页">
    {prev}
    <a href="index.html">目录</a>
    {next}
  </nav>
</div>

</body>
</html>
"""


def page_desc(raw, limit=88):
    """首页卡片摘要。

    优先用 H1 之后的第一段引用（`> ...`）—— 那通常是作者手写的导语，最像"摘要"。
    退而求其次才取第一段正文。早先是直接扫第一段非标题行，结果抓到了
    代码块/表格里的碎片（"root {"、"Commons api.php?action=..."），首页很难看。
    """
    lines = raw.split("\n")
    start = 0
    for i, l in enumerate(lines):
        if re.match(r"^#\s", l):
            start = i + 1
            break

    quote = []
    for l in lines[start:]:
        s = l.strip()
        if s.startswith(">"):
            quote.append(s.lstrip("> ").strip())
        elif quote:
            break
        elif s and not s.startswith(("#", "---", "|", "```")):
            break
    text = " ".join(quote)

    if len(text) < 20:                      # 没有导语，退回第一段正文
        plain = re.sub(r"(?ms)^```.*?^```\s*$", "", raw)
        plain = re.sub(r"(?m)^\s*[|>#].*$", "", plain)
        for l in plain.split("\n"):
            s = l.strip()
            if len(s) < 20 or s.startswith(("-", "*", "`", "!", "http")):
                continue
            if re.match(r"^\d+[.、]\s", s):
                continue
            text = s
            break

    text = re.sub(r"[*`]", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def build():
    # 清空上一次的产物（只删 .html/.css，不动任何源文件）
    if os.path.isdir(OUT):
        for f in os.listdir(OUT):
            p = os.path.join(OUT, f)
            if os.path.isdir(p):
                shutil.rmtree(p)
            elif f.endswith((".html", ".css")):
                os.remove(p)
    os.makedirs(os.path.join(OUT, "kit"), exist_ok=True)

    pages = collect_pages()
    total = len(pages)
    all_outside, link_warn, parse_warn = [], [], []
    n_total_unlinked = [0]
    fonts = []

    for i, page in enumerate(pages, 1):
        src = os.path.join(ROOT, os.path.splitext(page)[0] + ".md")
        with open(src, encoding="utf-8") as f:
            raw = f.read()

        raw, outside, n_rewritten, n_unlinked = rewrite_links(raw)
        n_total_unlinked[0] += n_unlinked
        all_outside += ["%s → %s" % (page, o) for o in outside]

        body = md_to_html(raw)
        title = first_h1(raw, os.path.splitext(page)[0])

        n_out = len(re.findall(r'href="\./[^"]+\.html(?:#[^"]*)?"', body))
        if n_out < n_rewritten:
            link_warn.append("%s：源 %d 条站内链接，产物只生成 %d 条" % (page, n_rewritten, n_out))

        # 自检①：围栏代码块 ``` 必须成对。奇数 = 没闭合，会把后半篇整个吞成代码块。
        n_fence = len(re.findall(r"(?m)^\s*```", raw))
        if n_fence % 2:
            parse_warn.append("%s：``` 出现 %d 次（奇数，没闭合）" % (page, n_fence))

        # 自检②：源里的标题数应≈产物里的 <h1..h4> 数。
        # 先剥掉围栏代码块再数 —— 否则代码里的 `# 注释` 会被当成标题（误报）。
        # 真出问题时（围栏没闭合）整篇被吞成代码块，剥完代码块标题数会骤降，这条依然抓得住。
        raw_nocode = re.sub(r"(?ms)^\s*```.*?^\s*```\s*$", "", raw)
        n_src_h = len(re.findall(r"(?m)^#{1,4}\s", raw_nocode))
        n_out_h = len(re.findall(r"<h[1-4][\s>]", body))
        if n_out_h < n_src_h:
            parse_warn.append("%s：源 %d 个标题，产物只解析出 %d 个" % (page, n_src_h, n_out_h))

        prev_a = ('<a href="%s">← %s</a>' % (pages[i - 2], os.path.splitext(pages[i - 2])[0])
                  if i > 1 else "<span></span>")
        next_a = ('<a href="%s">%s →</a>' % (pages[i], os.path.splitext(pages[i])[0])
                  if i < total else "<span></span>")

        out = PAGE.format(title=title, site=SITE_TITLE, desc=title,
                          no="%02d / %02d" % (i, total), body=body.rstrip(),
                          prev=prev_a, next=next_a)
        dst = os.path.join(OUT, page)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(out)
        print("  [OK] %-32s %6.1f KB" % (page, os.path.getsize(dst) / 1024))

    # ---------- 站点首页 ----------
    cards = []
    for i, page in enumerate(pages, 1):
        with open(os.path.join(ROOT, os.path.splitext(page)[0] + ".md"), encoding="utf-8") as f:
            raw = f.read()
        t = first_h1(raw, page)
        desc = page_desc(raw)
        cards.append("""      <a class="card" href="{href}">
        <span class="card__no">{no}</span>
        <h2 class="card__t">{t}</h2>
        <p class="card__d">{d}</p>
      </a>""".format(href=page, no="A" if i <= 6 else "B", t=t, d=desc))

    index = INDEX.format(site=SITE_TITLE, sub=SITE_SUB, cards="\n".join(cards))
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as f:
        f.write(index)
    print("  [OK] %-32s %6.1f KB" % ("index.html", len(index.encode()) / 1024))

    # ---------- 静态资源 ----------
    shutil.copy2(os.path.join(ROOT, "doc.css"), os.path.join(OUT, "doc.css"))
    for f in ("kv.css", "index.html"):
        shutil.copy2(os.path.join(ROOT, "kit", f), os.path.join(OUT, "kit", f))
        if f.endswith(".css"):
            # 只认字体域名：kv.css 里还有 SVG 命名空间之类的 URL，全扫会误报
            fonts += re.findall(
                r"https?://(?:fonts\.googleapis\.com|fonts\.gstatic\.com)[^\"'\s)]*",
                open(os.path.join(ROOT, "kit", f), encoding="utf-8").read())
    print("  [OK] %-32s（doc.css + kit/）" % "静态资源")

    # ---------- 体检 ----------
    print("\n  上线目录: %s" % OUT)
    exts = {}
    for dirpath, _, files in os.walk(OUT):
        for f in files:
            exts[os.path.splitext(f)[1] or "(无扩展名)"] = exts.get(os.path.splitext(f)[1] or "(无扩展名)", 0) + 1
    print("  文件类型: " + "  ".join("%s×%d" % (k, v) for k, v in sorted(exts.items())))
    bad = [e for e in exts if e not in (".html", ".css")]
    print("  %s" % ("✅ 只有 html/css，符合「不放其他东西」" if not bad
                    else "❌ 混入了非网页文件: " + ", ".join(bad)))
    if n_total_unlinked[0]:
        print("  已把 %d 条指向未上线路径（verify/ 等）的链接降级成纯文字，避免线上死链"
              % n_total_unlinked[0])

    if fonts:
        print("\n  ⚠️ 外部字体依赖（来自 kit/kv.css）：%s…" % sorted(set(fonts))[0][:66])
        print("     读者断网 / 大陆网络下会退化成系统字体：版面不塌，但窄体黑体特征会失去。")

    for label, items in (("Markdown 解析异常", parse_warn),
                         ("站内链接改写异常", link_warn),
                         ("指向站外的链接", all_outside)):
        if items:
            print("\n  ⚠️ %s：" % label)
            for x in items:
                print("     " + x)

    print("\n  共 %d 篇 + 首页。上线时把「上线」目录整体传上去即可。" % total)


INDEX = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{site}</title>
<meta name="description" content="{sub}">
<!-- 分享卡片：微信/QQ/X 抓的是这几条。og:url 必须是完整网址，相对路径不认。 -->
<meta property="og:type" content="website">
<meta property="og:site_name" content="{site}">
<meta property="og:title" content="{site}">
<meta property="og:description" content="{sub}">
<meta property="og:url" content="https://look4end.com/">
<meta property="og:locale" content="zh_CN">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{site}">
<meta name="twitter:description" content="{sub}">
<link rel="stylesheet" href="kit/kv.css">
<style>
  .home {{ position: relative; z-index: 2; max-width: 1440px; margin-inline: auto;
          padding: clamp(1.5rem,5vw,4rem) var(--kv-margin) clamp(4rem,9vw,8rem); }}
  .home__eyebrow {{ font-family: var(--kv-font-mono); font-size: .75rem;
        letter-spacing: .22em; text-transform: uppercase; color: var(--kv-red); margin: 0 0 .8rem; }}
  .home__title {{ font-family: var(--kv-font-alt); font-weight: 900;
        font-size: clamp(2.2rem,7.5vw,6rem); line-height: .9; letter-spacing: -.04em;
        text-transform: uppercase; margin: 0 0 .4rem; overflow-wrap: anywhere; }}
  .home__sub {{ font-family: var(--kv-font-display); font-weight: 400;
        font-size: clamp(.95rem,1.8vw,1.5rem); letter-spacing: .06em;
        margin: 0 0 clamp(1.5rem,4vw,2.5rem); color: var(--kv-ink-soft); }}
  .home__note {{ max-width: 70ch; margin: 0 0 clamp(2rem,5vw,3.5rem);
        border-left: var(--kv-rule) solid var(--kv-red); padding-left: 1.1rem; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fill,minmax(280px,1fr));
        gap: var(--kv-space-4); border-top: var(--kv-rule) solid var(--kv-ink); padding-top: var(--kv-space-5); }}
  .card {{ display: block; text-decoration: none; color: inherit; position: relative;
        border: 2px solid var(--kv-ink); background: var(--kv-paper-lift);
        padding: var(--kv-space-5) var(--kv-space-4) var(--kv-space-4);
        transition: transform var(--kv-dur-base) var(--kv-ease-mech),
                    box-shadow var(--kv-dur-base) var(--kv-ease-mech),
                    background-color var(--kv-dur-base) var(--kv-ease-mech); }}
  .card:hover {{ transform: translate(-4px,-4px) skewX(-3deg); box-shadow: var(--kv-shadow-red); }}
  .card:active {{ background: var(--kv-ink); color: var(--kv-paper); transform: none; box-shadow: none; }}
  .card__no {{ position: absolute; top: 0; left: 0; padding: .1rem .5rem;
        background: var(--kv-ink); color: var(--kv-paper);
        font-family: var(--kv-font-mono); font-size: .7rem; letter-spacing: .16em; }}
  .card:hover .card__no {{ background: var(--kv-red); }}
  .card__t {{ font-family: var(--kv-font-display); font-weight: 700;
        font-size: clamp(1.05rem,1.9vw,1.5rem); line-height: 1.06;
        letter-spacing: -.01em; text-transform: uppercase; margin: 0 .2rem .5rem; }}
  .card__d {{ margin: 0 .2rem; font-size: .875rem; line-height: 1.55; color: var(--kv-ink-soft); }}
  .card:active .card__d {{ color: var(--kv-paper); }}
  .home__foot {{ margin-top: clamp(2.5rem,6vw,4rem); padding-top: 1rem;
        border-top: var(--kv-rule) solid var(--kv-ink);
        font-size: .8125rem; color: var(--kv-ink-soft); }}
  .home__foot a {{ color: inherit; }}
</style>
</head>
<body>

<div class="kv-axis" aria-hidden="true"></div>

<div class="home">
  <p class="home__eyebrow">Constructivism · Design Notes</p>
  <h1 class="home__title">构成主义<br>HTML 设计</h1>
  <p class="home__sub">{sub}</p>

  <p class="home__note">
    这一组文档记录的是「设计 HTML」这件事本身：一个具体风格的美学考据，
    加上实现过程中沉淀下来的、可跨项目复用的规则与踩坑。
    所有关键数值都经过实测或精算，未验证的部分明确标注。
  </p>

  <div class="cards">
{cards}
  </div>

  <div class="home__foot">
    可运行的样式套件与样式指南：<a href="kit/index.html">kit/index.html</a>
  </div>
</div>

</body>
</html>
"""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="把 .md 构建成站点页面（产物只有 .html 和 .css）")
    ap.add_argument("--out", default=OUT,
                    help="产物目录。默认自动判定：在仓库 src/notes/ 下就写 ../../notes/，否则写 ./上线/")
    args = ap.parse_args()
    OUT = os.path.abspath(args.out)
    print("构建上线目录：")
    build()
