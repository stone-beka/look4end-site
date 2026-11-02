# 时间门 + 时代包 重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 look4end.com 从「根层就是苏联报纸」改成「极简时间门 + 物理独立的时代包」，让以后新增美学时代只新增目录、不改旧代码。

**Architecture:** 根层只生成极简索引 `/index.html`、`sitemap.xml`、`_redirects`；每个时代是 `eras/<slug>/` 下的自包含包（页面/样式/脚本/素材/源/产物/构建脚本/说明）；`tools/build_all.py` 统一调度并做五项体检。

**Tech Stack:** 纯静态 HTML/CSS/JS；Python 3 标准库 + `markdown`（唯一第三方依赖）；Node 仅用于既有浏览器测试脚本；Cloudflare Pages 直接部署仓库根。

**设计依据：** `docs/superpowers/specs/2026-11-02-era-architecture-design.md`

---

## Global Constraints

- 仓库根 = `C:\Users\23077\Desktop\work_place\网页制作工作区`；本计划所有路径相对它。
- 不引入任何新依赖；Python 只用标准库 + `markdown`；不引入打包器。
- 生成物提交进 git（Cloudflare Pages 直接从仓库部署，没有构建步骤）：`index.html`、`core/eras.json`、`sitemap.xml`、`_redirects`、`eras/*/notes/`、`eras/*/motion/` 的文档产物。
- 构建幂等：连续两次 `python tools/build_all.py` 后 `git diff --exit-code` 必须为空。生成物里禁止出现时间戳、绝对路径、随机数。
- 站内链接一律**相对路径**，禁止以 `/` 开头。
- 根层禁止出现任何时代专属文案、色值、字体名；时代内文件禁止引用其他时代、`core/`、`tools/`。
- 产物目录只允许 `.html` `.css` `.js` 和图片。
- 中文文件名保持现状（线上已验证可用）；`.bat`/`.ps1` 不动。
- 每个任务结束跑一次 `git status` 确认没有意外文件，并按任务里的提交信息提交一次（中文）。
- 提交前先 `python tools/build_all.py` 通过；涉及浏览器的验收命令单独标注。

---

## 文件地图（目标态）

| 文件 | 责任 |
|---|---|
| `tools/era_lib.py` | 纯函数：校验 era.json、扫描页面、生成 sitemap/redirects/registry/门 |
| `tools/build_all.py` | 调度器：跑各 era 构建 → 生成四件套 → 五项体检 |
| `tools/templates/gate.html` | 门模板（`{{CSS}}` `{{INTRO}}` `{{ERAS}}` 三个占位） |
| `tools/tests/test_era_lib.py` | 纯函数单测 |
| `tools/tests/test_build_all.py` | 调度器集成测试（临时 fixture 仓库） |
| `tools/verify/run_all.py` | 一条命令跑：构建 → 单测 → 静态检查 → 路由测试 |
| `core/gate.css` | 门的基础排版（≤80 行，系统字体） |
| `eras/_template/**` | 新时代脚手架 |
| `eras/soviet-1923/**` | 苏联时代包（现有内容迁入） |
| `docs/ERA-CONTRACT.md` | 时代接口契约（做新时代只读这份） |

---

## Task 1: 规则层 `tools/era_lib.py` + 单测

**Files:**
- Create: `tools/era_lib.py`
- Create: `tools/tests/test_era_lib.py`

**Interfaces:**
- Produces:
  - `SITE: str`、`SLUG_RE: re.Pattern`、`STATUSES: tuple`
  - `validate_era(era: dict, dirname: str | None = None) -> list[str]`
  - `load_eras(root: str) -> tuple[list[dict], list[str]]`（按 order 排序，每项带 `_dir` 绝对路径）
  - `render_redirects(eras: list[dict]) -> str`
  - `scan_pages(root: str) -> list[str]`（仓库相对路径，正斜杠）
  - `url_for(rel: str) -> str`
  - `render_sitemap(pages: list[str]) -> str`
  - `render_registry(eras: list[dict]) -> str`
  - `render_gate(eras: list[dict], template: str, css: str, intro: str) -> str`

- [ ] **Step 1: 写失败测试**

创建 `tools/tests/test_era_lib.py`：

```python
# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import era_lib  # noqa: E402


def era(**kw):
    base = {
        "slug": "demo-1900",
        "order": 10,
        "name": "演示时代",
        "years": "1900",
        "summary": "一句话说明。",
        "status": "published",
    }
    base.update(kw)
    return base


class ValidateEraTest(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(era_lib.validate_era(era(), "demo-1900"), [])

    def test_slug_must_equal_dirname(self):
        self.assertTrue(era_lib.validate_era(era(), "other-dir"))

    def test_slug_format(self):
        self.assertTrue(era_lib.validate_era(era(slug="Demo_1900"), "Demo_1900"))

    def test_order_must_be_int(self):
        self.assertTrue(era_lib.validate_era(era(order="10"), "demo-1900"))
        self.assertTrue(era_lib.validate_era(era(order=True), "demo-1900"))

    def test_status_enum(self):
        self.assertTrue(era_lib.validate_era(era(status="live"), "demo-1900"))

    def test_summary_length(self):
        self.assertTrue(era_lib.validate_era(era(summary="长" * 61), "demo-1900"))

    def test_missing_field(self):
        bad = era()
        del bad["years"]
        self.assertTrue(era_lib.validate_era(bad, "demo-1900"))


class LoadErasTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.tmp, "eras"))

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_era(self, slug, **kw):
        d = os.path.join(self.tmp, "eras", slug)
        os.makedirs(d)
        data = era(slug=slug, **kw)
        with open(os.path.join(d, "era.json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        return d

    def test_sorted_and_skip_template(self):
        self.write_era("b-2", order=20)
        self.write_era("a-1", order=10)
        os.makedirs(os.path.join(self.tmp, "eras", "_template"))
        with open(os.path.join(self.tmp, "eras", "_template", "era.json"), "w", encoding="utf-8") as fh:
            json.dump(era(slug="template"), fh)
        eras, errors = era_lib.load_eras(self.tmp)
        self.assertEqual(errors, [])
        self.assertEqual([e["slug"] for e in eras], ["a-1", "b-2"])

    def test_duplicate_order(self):
        self.write_era("a-1", order=10)
        self.write_era("b-2", order=10)
        eras, errors = era_lib.load_eras(self.tmp)
        self.assertTrue(any("order 10 重复" in e for e in errors))

    def test_bad_json(self):
        d = os.path.join(self.tmp, "eras", "x-1")
        os.makedirs(d)
        with open(os.path.join(d, "era.json"), "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        eras, errors = era_lib.load_eras(self.tmp)
        self.assertTrue(errors)


class RedirectsTest(unittest.TestCase):
    def test_soviet_legacy(self):
        out = era_lib.render_redirects([era(slug="soviet-1923", legacy=["/notes/", "/motion/", "/assets/"])])
        self.assertIn("/notes /soviet-1923/notes 301", out)
        self.assertIn("/notes/* /soviet-1923/notes/:splat 301", out)
        self.assertIn("/motion/* /soviet-1923/motion/:splat 301", out)
        self.assertIn("/assets/* /soviet-1923/assets/:splat 301", out)

    def test_no_legacy_no_rules(self):
        out = era_lib.render_redirects([era()])
        self.assertNotIn("301", out)


class SitemapTest(unittest.TestCase):
    def test_url_for(self):
        self.assertEqual(era_lib.url_for("index.html"), era_lib.SITE + "/")
        self.assertEqual(era_lib.url_for("eras/a-1/index.html"), era_lib.SITE + "/eras/a-1/")
        self.assertEqual(era_lib.url_for("eras/a-1/notes/x.html"), era_lib.SITE + "/eras/a-1/notes/x")

    def test_sitemap_sorted_and_unique(self):
        pages = ["index.html", "eras/a-1/index.html", "eras/a-1/index.html"]
        xml = era_lib.render_sitemap(pages)
        self.assertIn("<loc>%s/</loc>" % era_lib.SITE, xml)
        self.assertEqual(xml.count("/eras/a-1/"), 1)

    def test_scan_skips_sources_and_tools(self):
        tmp = tempfile.mkdtemp()
        try:
            for rel in ("index.html", "404.html", "eras/a-1/index.html",
                        "eras/a-1/notes/x.html", "eras/a-1/src/notes/kit/index.html",
                        "eras/_template/index.html", "tools/templates/gate.html",
                        "docs/specs/x.html", "core/eras.json"):
                p = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "w", encoding="utf-8").close()
            pages = era_lib.scan_pages(tmp)
            self.assertIn("index.html", pages)
            self.assertIn("eras/a-1/notes/x.html", pages)
            self.assertNotIn("404.html", pages)
            self.assertNotIn("eras/a-1/src/notes/kit/index.html", pages)
            self.assertNotIn("eras/_template/index.html", pages)
            self.assertNotIn("tools/templates/gate.html", pages)
            self.assertNotIn("docs/specs/x.html", pages)
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


class GateTest(unittest.TestCase):
    TMPL = "<h1>门</h1>{{CSS}}{{INTRO}}<ul>{{ERAS}}</ul>"

    def test_published_only_and_escape(self):
        eras = [era(slug="a-1", name="A&B", summary="<x>"), era(slug="b-2", order=20, status="draft")]
        out = era_lib.render_gate(eras, self.TMPL, "body{}", "说明")
        self.assertIn("a-1/", out)
        self.assertIn("A&amp;B", out)
        self.assertNotIn("b-2", out)
        self.assertIn("说明", out)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行，确认失败**

Run: `python -m unittest discover -s tools/tests -t tools -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'era_lib'`（文件还不存在）。

- [ ] **Step 3: 写实现**

创建 `tools/era_lib.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""era_lib.py —— 多时代站点的纯函数规则层（无副作用，便于单测）"""
import html
import json
import os
import re

SITE = "https://look4end.com"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STATUSES = ("published", "draft")
REQUIRED = ("slug", "order", "name", "years", "summary", "status")
SKIP_TOP = {"tools", "docs", "core", "node_modules", "__pycache__"}

GATE_ITEM = """      <li class="era">
        <a class="era__link" href="{slug}/">
          <span class="era__years">{years}</span>
          <span class="era__name">{name}</span>
          <span class="era__summary">{summary}</span>
          <span class="era__go">进入 →</span>
        </a>
      </li>"""


def validate_era(era, dirname=None):
    """返回错误列表；空列表 = 通过。"""
    errors = []
    if not isinstance(era, dict):
        return ["era.json 必须是 JSON 对象"]
    for key in REQUIRED:
        if key not in era:
            errors.append("缺少字段 %s" % key)
    order = era.get("order")
    if not isinstance(order, int) or isinstance(order, bool):
        errors.append("order 必须是整数")
    slug = era.get("slug")
    if not isinstance(slug, str) or not SLUG_RE.match(slug):
        errors.append("slug 不合法（只允许小写字母/数字/连字符）：%r" % (slug,))
    elif dirname is not None and slug != dirname:
        errors.append("slug（%s）必须等于目录名（%s）" % (slug, dirname))
    if era.get("status") not in STATUSES:
        errors.append("status 必须是 published 或 draft")
    for key in ("name", "years"):
        value = era.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append("%s 必须是非空字符串" % key)
    summary = era.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        errors.append("summary 必须是非空字符串")
    elif len(summary) > 60:
        errors.append("summary 超过 60 字（当前 %d）" % len(summary))
    for key in ("notes", "motion"):
        if key in era and not isinstance(era[key], dict):
            errors.append("%s 必须是对象" % key)
    legacy = era.get("legacy")
    if legacy is not None and not (
        isinstance(legacy, list) and all(isinstance(x, str) for x in legacy)
    ):
        errors.append("legacy 必须是字符串数组")
    return errors


def era_dirs(root):
    base = os.path.join(root, "eras")
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if name.startswith("_") or not os.path.isdir(path):
            continue
        if os.path.isfile(os.path.join(path, "era.json")):
            out.append((name, path))
    return out


def load_eras(root):
    eras, errors = [], []
    for name, path in era_dirs(root):
        try:
            with open(os.path.join(path, "era.json"), encoding="utf-8") as fh:
                era = json.load(fh)
        except (OSError, ValueError) as exc:
            errors.append("%s: era.json 读取失败：%s" % (name, exc))
            continue
        problems = validate_era(era, name)
        if problems:
            errors.extend("%s: %s" % (name, p) for p in problems)
            continue
        era["_dir"] = path
        eras.append(era)
    seen = {}
    for era in eras:
        seen.setdefault(era["order"], []).append(era["slug"])
    for order, slugs in sorted(seen.items()):
        if len(slugs) > 1:
            errors.append("order %d 重复：%s" % (order, "、".join(slugs)))
    eras.sort(key=lambda e: (e["order"], e["slug"]))
    return eras, errors


def render_redirects(eras):
    lines = ["# 由 tools/build_all.py 生成，不要手改"]
    for era in eras:
        slug = era["slug"]
        for legacy in era.get("legacy", []):
            prefix = legacy.strip("/")
            if not prefix:
                continue
            lines.append("/%s /%s/%s 301" % (prefix, slug, prefix))
            lines.append("/%s/* /%s/%s/:splat 301" % (prefix, slug, prefix))
    return "\n".join(lines) + "\n"


def _skip_dir(rel_dir):
    parts = [p for p in rel_dir.split("/") if p]
    if not parts:
        return False
    if parts[0] in SKIP_TOP or parts[0].startswith(("_", ".")):
        return True
    if "src" in parts or "__pycache__" in parts:
        return True
    if len(parts) >= 2 and parts[0] == "eras" and parts[1].startswith("_"):
        return True
    return False


def scan_pages(root):
    pages = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        rel_dir = "" if rel_dir == "." else rel_dir
        dirnames[:] = sorted(
            d for d in dirnames
            if not _skip_dir("/".join(x for x in (rel_dir, d) if x))
        )
        for name in sorted(filenames):
            if not name.endswith(".html") or name.startswith("_") or name == "404.html":
                continue
            pages.append("/".join(x for x in (rel_dir, name) if x))
    return sorted(pages)


def url_for(rel):
    rel = rel.replace(os.sep, "/")
    if rel == "index.html":
        return SITE + "/"
    if rel.endswith("/index.html"):
        return SITE + "/" + rel[: -len("index.html")]
    if rel.endswith(".html"):
        return SITE + "/" + rel[: -len(".html")]
    raise ValueError("不是 HTML 页面：%s" % rel)


def render_sitemap(pages):
    urls = sorted({url_for(p) for p in pages})
    body = "\n".join("  <url>\n    <loc>%s</loc>\n  </url>" % html.escape(u) for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body
        + "\n</urlset>\n"
    )


REGISTRY_FIELDS = ("slug", "order", "name", "years", "summary", "notes", "motion", "entry")


def render_registry(eras):
    items = [
        {k: era[k] for k in REGISTRY_FIELDS if k in era}
        for era in eras
        if era["status"] == "published"
    ]
    return json.dumps({"site": SITE, "eras": items}, ensure_ascii=False, indent=2) + "\n"


def render_gate(eras, template, css, intro):
    items = [
        GATE_ITEM.format(
            slug=html.escape(era["slug"]),
            years=html.escape(era["years"]),
            name=html.escape(era["name"]),
            summary=html.escape(era["summary"]),
        )
        for era in eras
        if era["status"] == "published"
    ]
    return (
        template.replace("{{CSS}}", css.strip())
        .replace("{{INTRO}}", html.escape(intro.strip()))
        .replace("{{ERAS}}", "\n".join(items))
    )
```

- [ ] **Step 4: 运行，确认通过**

Run: `python -m unittest discover -s tools/tests -t tools -v`
Expected: 全部 PASS（约 14 个用例）。

- [ ] **Step 5: 提交**

```bash
git add tools/era_lib.py tools/tests/test_era_lib.py
git commit -m "feat(tools): 时代规则层 era_lib + 单测"
```

---

## Task 2: 门模板 `gate.html` + `core/gate.css`

**Files:**
- Create: `tools/templates/gate.html`
- Create: `core/gate.css`
- Modify: `tools/tests/test_era_lib.py`（追加渲染用例）

**Interfaces:**
- Produces: 门模板三个占位 `{{CSS}}` `{{INTRO}}` `{{ERAS}}`，供 `render_gate()` 使用；`core/gate.css` 必须 ≤80 行、系统字体、无 `@import`。

- [ ] **Step 1: 写失败测试**

在 `tools/tests/test_era_lib.py` 追加：

```python
class GateRenderIntegrationTest(unittest.TestCase):
    def test_template_and_css_are_safe(self):
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        with open(os.path.join(repo, "tools", "templates", "gate.html"), encoding="utf-8") as fh:
            tmpl = fh.read()
        with open(os.path.join(repo, "core", "gate.css"), encoding="utf-8") as fh:
            css = fh.read()
        out = era_lib.render_gate([era(slug="a-1", name="甲")], tmpl, css, "说明")
        self.assertIn("a-1/", out)
        self.assertNotIn("{{", out)
        self.assertNotIn("<script", out.lower())
        self.assertNotIn("fonts.googleapis", out)
        self.assertNotIn("@import", out)
        self.assertLessEqual(len(css.splitlines()), 80)
```

- [ ] **Step 2: 运行，确认失败**

Run: `python -m unittest discover -s tools/tests -t tools -v`
Expected: FAIL — `FileNotFoundError: .../tools/templates/gate.html`。

- [ ] **Step 3: 写模板与样式**

创建 `tools/templates/gate.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Look4End · 时代档案</title>
<meta name="description" content="按时代陈列的视觉美学档案。选一个时代走进去。">
<meta property="og:type" content="website">
<meta property="og:title" content="Look4End · 时代档案">
<meta property="og:description" content="按时代陈列的视觉美学档案。">
<meta property="og:url" content="https://look4end.com/">
<style>
{{CSS}}
</style>
</head>
<body>
<main class="gate">
  <h1 class="gate__title">Look4End</h1>
  <p class="gate__intro">{{INTRO}}</p>
  <ul class="eras">
{{ERAS}}
  </ul>
  <footer class="gate__foot">
    <p>每个时代是一个独立的世界。选一个进去。</p>
  </footer>
</main>
</body>
</html>
```

创建 `core/gate.css`：

```css
:root {
  color-scheme: light;
  --ink: #111;
  --paper: #f7f5f0;
  --muted: #555;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: -apple-system, "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
  line-height: 1.5;
}
.gate { max-width: 62rem; margin: 0 auto; padding: clamp(2rem, 6vw, 5rem) 1.25rem 4rem; }
.gate__title { margin: 0 0 .5rem; font-size: clamp(1.6rem, 4vw, 2.4rem); letter-spacing: .02em; }
.gate__intro { margin: 0 0 2.5rem; color: var(--muted); max-width: 40ch; }
.eras { list-style: none; margin: 0; padding: 0; border-top: 2px solid var(--ink); }
.era { border-bottom: 1px solid #c9c4b8; }
.era__link {
  display: grid;
  grid-template-columns: 8rem 1fr auto;
  gap: .35rem 1.25rem;
  align-items: baseline;
  padding: 1.1rem .25rem;
  color: inherit;
  text-decoration: none;
}
.era__years { font-variant-numeric: tabular-nums; color: var(--muted); font-size: .9rem; }
.era__name { font-weight: 700; }
.era__summary { grid-column: 2; grid-row: 2; color: var(--muted); font-size: .9rem; }
.era__go { grid-column: 3; grid-row: 1 / span 2; font-size: .9rem; }
.era__link:hover .era__name { text-decoration: underline; }
.era__link:focus-visible { outline: 3px solid var(--ink); outline-offset: 3px; }
.gate__foot { margin-top: 3rem; color: var(--muted); font-size: .85rem; }
@media (max-width: 34rem) {
  .era__link { grid-template-columns: 1fr auto; }
  .era__years { grid-column: 1; grid-row: 1; }
  .era__name { grid-column: 1; grid-row: 2; }
  .era__summary { grid-column: 1; grid-row: 3; }
  .era__go { grid-column: 2; grid-row: 1 / span 3; align-self: center; }
}
```

- [ ] **Step 4: 运行，确认通过**

Run: `python -m unittest discover -s tools/tests -t tools -v`
Expected: 全部 PASS。

- [ ] **Step 5: 提交**

```bash
git add tools/templates/gate.html core/gate.css tools/tests/test_era_lib.py
git commit -m "feat(gate): 极简时间门模板与基础样式"
```

---

## Task 3: 调度器 `tools/build_all.py` + 集成测试

**Files:**
- Create: `tools/build_all.py`
- Create: `tools/tests/test_build_all.py`

**Interfaces:**
- Consumes: `era_lib`（Task 1）、`tools/templates/gate.html` 与 `core/gate.css`（Task 2）。
- Produces:
  - CLI：`python tools/build_all.py [--root DIR] [--skip-build]`，退出码 0/1。
  - 写出：`<root>/index.html`、`<root>/core/eras.json`、`<root>/sitemap.xml`、`<root>/_redirects`。
  - 体检函数：`check_links(root)`、`check_isolation(root, eras)`、`check_products(eras)`、`check_gate(text)`，均返回 `list[str]` 失败项。

- [ ] **Step 1: 写失败测试**

创建 `tools/tests/test_build_all.py`：

```python
# -*- coding: utf-8 -*-
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(TOOLS)
BUILD = os.path.join(TOOLS, "build_all.py")


class BuildAllTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        shutil.copytree(os.path.join(REPO, "tools", "templates"), os.path.join(self.tmp, "tools", "templates"))
        os.makedirs(os.path.join(self.tmp, "core"))
        shutil.copy2(os.path.join(REPO, "core", "gate.css"), os.path.join(self.tmp, "core", "gate.css"))
        os.makedirs(os.path.join(self.tmp, "eras"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_era(self, slug, order, status="published", broken=False, body="笔记"):
        d = os.path.join(self.tmp, "eras", slug)
        os.makedirs(d)
        data = {"slug": slug, "order": order, "name": slug + "名", "years": "1900",
                "summary": "一句话。", "status": status}
        with open(os.path.join(d, "era.json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        href = "missing.html" if broken else "notes/"
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write('<!DOCTYPE html><html><body><a href="%s">%s</a></body></html>' % (href, body))
        os.makedirs(os.path.join(d, "notes"))
        with open(os.path.join(d, "notes", "index.html"), "w", encoding="utf-8") as fh:
            fh.write("<!DOCTYPE html><html><body>ok</body></html>")
        with open(os.path.join(d, "build.py"), "w", encoding="utf-8") as fh:
            fh.write("print('built')\n")
        return d

    def run_build(self, *extra):
        return subprocess.run(
            [sys.executable, BUILD, "--root", self.tmp, *extra],
            capture_output=True, text=True, encoding="utf-8",
        )

    def test_happy_path(self):
        self.make_era("a-1", 10)
        self.make_era("b-2", 20)
        proc = self.run_build()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        gate = open(os.path.join(self.tmp, "index.html"), encoding="utf-8").read()
        self.assertIn("a-1/", gate)
        self.assertIn("b-2/", gate)
        self.assertNotIn("<script", gate.lower())
        registry = json.load(open(os.path.join(self.tmp, "core", "eras.json"), encoding="utf-8"))
        self.assertEqual([e["slug"] for e in registry["eras"]], ["a-1", "b-2"])
        sitemap = open(os.path.join(self.tmp, "sitemap.xml"), encoding="utf-8").read()
        self.assertIn("/a-1/", sitemap)
        self.assertIn("/a-1/notes/", sitemap)
        self.assertIn("/b-2/notes/", sitemap)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "_redirects")))

    def test_draft_excluded(self):
        self.make_era("a-1", 10)
        self.make_era("d-9", 90, status="draft")
        proc = self.run_build()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        gate = open(os.path.join(self.tmp, "index.html"), encoding="utf-8").read()
        sitemap = open(os.path.join(self.tmp, "sitemap.xml"), encoding="utf-8").read()
        self.assertNotIn("d-9", gate)
        self.assertNotIn("d-9", sitemap)

    def test_duplicate_order_fails(self):
        self.make_era("a-1", 10)
        self.make_era("b-2", 10)
        proc = self.run_build()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("order 10 重复", proc.stderr)

    def test_broken_link_fails(self):
        self.make_era("a-1", 10, broken=True)
        proc = self.run_build()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("missing.html", proc.stderr + proc.stdout)

    def test_build_script_failure_fails(self):
        d = self.make_era("a-1", 10)
        with open(os.path.join(d, "build.py"), "w", encoding="utf-8") as fh:
            fh.write("import sys\nsys.exit(3)\n")
        proc = self.run_build()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("构建失败", proc.stderr)

    def test_idempotent(self):
        self.make_era("a-1", 10)
        self.assertEqual(self.run_build().returncode, 0)
        first = {p: open(os.path.join(self.tmp, p), "rb").read()
                 for p in ("index.html", "core/eras.json", "sitemap.xml", "_redirects")}
        self.assertEqual(self.run_build().returncode, 0)
        second = {p: open(os.path.join(self.tmp, p), "rb").read()
                  for p in ("index.html", "core/eras.json", "sitemap.xml", "_redirects")}
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行，确认失败**

Run: `python -m unittest discover -s tools/tests -t tools -v`
Expected: FAIL — 找不到 `build_all.py`（`FileNotFoundError` 或子进程返回非 0）。

- [ ] **Step 3: 写实现**

创建 `tools/build_all.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_all.py —— 多时代站点调度器

跑每个时代的 build.py，然后生成门 / 注册表 / sitemap / _redirects，最后做五项体检。
用法：python tools/build_all.py [--root DIR] [--skip-build]
退出码：0 = 全过；1 = 任何一步失败。
"""
import argparse
import os
import re
import subprocess
import sys

import era_lib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTRO = "这里按时代陈列视觉美学。每个时代都是独立的世界，页面、字体、动效互不共享。"
LINK_RE = re.compile(r'(?:href|src)="([^"]+)"')
EXTERNAL = ("http://", "https://", "mailto:", "data:", "javascript:", "//", "#")
PRODUCT_EXTS = {".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif", ".ico", ".woff", ".woff2"}


def run_era_build(era):
    script = era.get("build", "build.py")
    path = os.path.join(era["_dir"], script)
    if not os.path.isfile(path):
        raise SystemExit("[%s] 缺少构建脚本 %s" % (era["slug"], script))
    print("── 构建 %s" % era["slug"])
    proc = subprocess.run(
        [sys.executable, path], cwd=era["_dir"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr.rstrip(), file=sys.stderr)
        raise SystemExit("[%s] 构建失败（退出码 %d）" % (era["slug"], proc.returncode))


def write_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("  生成 %s" % os.path.relpath(path, ROOT))


def _era_web_files(era_dir):
    for dirpath, dirnames, filenames in os.walk(era_dir):
        dirnames[:] = [d for d in dirnames if d not in {"src", "__pycache__", ".git"}]
        for name in filenames:
            if name.endswith((".html", ".css", ".js")):
                yield os.path.join(dirpath, name)


def check_links(root):
    failures = []
    for rel in era_lib.scan_pages(root):
        path = os.path.join(root, rel)
        base = os.path.dirname(path)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for target in LINK_RE.findall(text):
            if target.startswith(EXTERNAL):
                continue
            clean = target.split("#", 1)[0].split("?", 1)[0]
            if not clean:
                continue
            resolved = os.path.normpath(os.path.join(base, clean))
            if os.path.isdir(resolved):
                if not os.path.isfile(os.path.join(resolved, "index.html")):
                    failures.append("%s -> %s（目录里没有 index.html）" % (rel, target))
            elif not os.path.isfile(resolved):
                failures.append("%s -> %s（不存在）" % (rel, target))
    return failures


def check_isolation(root, eras):
    failures = []
    for era in eras:
        slug = era["slug"]
        era_dir = os.path.abspath(era["_dir"])
        for path in _era_web_files(era_dir):
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            for ref in LINK_RE.findall(text):
                if ref.startswith(EXTERNAL):
                    continue
                clean = ref.split("#", 1)[0].split("?", 1)[0]
                if not clean:
                    continue
                if clean.startswith("/"):
                    if not (clean == "/" + slug or clean.startswith("/" + slug + "/")):
                        failures.append("%s: 绝对路径 %s（应改相对路径）" % (rel, ref))
                    continue
                resolved = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(path), clean)))
                if resolved != era_dir and not resolved.startswith(era_dir + os.sep):
                    failures.append("%s: 引用跑出时代目录 -> %s" % (rel, ref))
    return failures


def check_products(eras):
    failures = []
    for era in eras:
        dirs = []
        if "notes" in era:
            dirs.append(os.path.join(era["_dir"], era["notes"].get("dir", "notes")))
        motion_entry = era.get("motion", {}).get("entry")
        if motion_entry:
            dirs.append(os.path.dirname(os.path.join(era["_dir"], motion_entry)))
        for out_dir in dirs:
            if not os.path.isdir(out_dir):
                failures.append("%s: 产物目录不存在 %s" % (era["slug"], out_dir))
                continue
            for dirpath, _, filenames in os.walk(out_dir):
                for name in filenames:
                    ext = os.path.splitext(name)[1].lower()
                    if ext not in PRODUCT_EXTS:
                        failures.append("%s: 产物里混入 %s" % (era["slug"], os.path.join(dirpath, name)))
    return failures


def check_gate(text):
    failures = []
    lower = text.lower()
    if "<script" in lower:
        failures.append("门里出现了 <script>")
    if "fonts.googleapis" in lower or "fonts.gstatic" in lower:
        failures.append("门里加载了 Web 字体")
    if "<img" in lower:
        failures.append("门里出现了图片")
    return failures


def main():
    ap = argparse.ArgumentParser(description="构建所有时代并生成门")
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--skip-build", action="store_true", help="只重新生成门/注册表/sitemap，不跑时代构建")
    args = ap.parse_args()
    root = os.path.abspath(args.root)

    eras, errors = era_lib.load_eras(root)
    if errors:
        for item in errors:
            print("  [XX] " + item, file=sys.stderr)
        raise SystemExit("era.json 校验失败")

    if not args.skip_build:
        for era in eras:
            run_era_build(era)

    template = open(os.path.join(root, "tools", "templates", "gate.html"), encoding="utf-8").read()
    css = open(os.path.join(root, "core", "gate.css"), encoding="utf-8").read()
    gate = era_lib.render_gate(eras, template, css, INTRO)
    write_file(os.path.join(root, "index.html"), gate)
    write_file(os.path.join(root, "core", "eras.json"), era_lib.render_registry(eras))
    write_file(os.path.join(root, "_redirects"), era_lib.render_redirects(eras))
    pages = era_lib.scan_pages(root)
    write_file(os.path.join(root, "sitemap.xml"), era_lib.render_sitemap(pages))

    failures = (
        check_gate(gate)
        + check_links(root)
        + check_isolation(root, eras)
        + check_products(eras)
    )
    if failures:
        print("\n体检未通过：", file=sys.stderr)
        for item in failures:
            print("  [XX] " + item, file=sys.stderr)
        raise SystemExit(1)
    print("\n体检通过：%d 个时代，%d 个页面。" % (len(eras), len(pages)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行，确认通过**

Run: `python -m unittest discover -s tools/tests -t tools -v`
Expected: 全部 PASS（含 6 个集成用例）。若 `test_idempotent` 失败，检查是否写入了时间戳。

- [ ] **Step 5: 在真仓库空跑一次**

Run: `python tools/build_all.py`
Expected: 退出码 0；生成 `index.html`（暂无时代，只有一个空列表）、`core/eras.json`、`sitemap.xml`、`_redirects`；不要提交这四个文件（Task 6 才正式切换）。

Run: `git status --short`
Expected: 只有上述 4 个未跟踪/修改文件。

- [ ] **Step 6: 提交**

```bash
git add tools/build_all.py tools/tests/test_build_all.py
git commit -m "feat(tools): build_all 调度器 + 门/注册表/sitemap/redirects 生成 + 五项体检"
```

---

## Task 4: 时代脚手架 `eras/_template/` + 契约文档

**Files:**
- Create: `eras/_template/era.json`
- Create: `eras/_template/index.html`
- Create: `eras/_template/era.css`
- Create: `eras/_template/entry.css`
- Create: `eras/_template/build.py`
- Create: `eras/_template/AGENTS.md`
- Create: `eras/_template/src/notes/README.md`
- Create: `eras/_template/src/notes/01-美学考据.md`
- Create: `eras/_template/src/notes/doc.css`
- Create: `eras/_template/assets/.gitkeep`
- Create: `docs/ERA-CONTRACT.md`

**Interfaces:**
- Produces: 一个可复制、可构建的最小时代包；`python eras/_template/build.py` 能独立跑通（虽然 `_` 目录不进 build_all）。契约文档是以后做新时代唯一要读的跨时代文件。

- [ ] **Step 1: 写脚手架文件**

创建 `eras/_template/era.json`：

```json
{
  "slug": "template",
  "order": 999,
  "name": "（改我：时代名）",
  "years": "（改我：年代，如 1919–1925）",
  "summary": "（改我：一句话，不超过 60 字）",
  "status": "draft",
  "notes": { "dir": "notes", "label": "设计笔记" },
  "arrival": "entry.css"
}
```

创建 `eras/_template/index.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>（改我：时代名）</title>
<meta name="description" content="（改我：一句话）">
<link rel="stylesheet" href="era.css">
<link rel="stylesheet" href="entry.css">
</head>
<body class="era-template">
<main class="era">
  <p class="era__kicker">（改我：年代）</p>
  <h1 class="era__title">（改我：时代名）</h1>
  <p class="era__lead">整页都是这个时代的画布。把占位换成你自己的构图。</p>
  <p><a class="era__link" href="notes/">设计笔记 →</a></p>
  <p><a class="era__link" href="../">← 回时间门</a></p>
</main>
</body>
</html>
```

创建 `eras/_template/era.css`：

```css
:root {
  --era-ink: #111;
  --era-paper: #f7f5f0;
  --era-accent: #a02020;
}
html, body { margin: 0; }
body.era-template {
  background: var(--era-paper);
  color: var(--era-ink);
  font-family: "Noto Serif SC", "Songti SC", serif;
}
.era { min-height: 100vh; max-width: 64rem; margin: 0 auto; padding: 12vh 1.25rem; }
.era__kicker { letter-spacing: .3em; text-transform: uppercase; color: var(--era-accent); }
.era__title { font-size: clamp(2.5rem, 10vw, 7rem); line-height: .95; margin: .2em 0; }
.era__lead { max-width: 36ch; }
.era__link { color: inherit; }
```

创建 `eras/_template/entry.css`：

```css
@media (prefers-reduced-motion: no-preference) {
  .era > * { animation: era-in .7s cubic-bezier(.2, .7, .2, 1) both; }
  .era > :nth-child(2) { animation-delay: .08s; }
  .era > :nth-child(3) { animation-delay: .16s; }
  .era > :nth-child(4) { animation-delay: .24s; }
  @keyframes era-in {
    from { opacity: 0; transform: translateY(1.2rem); }
    to { opacity: 1; transform: none; }
  }
}
```

创建 `eras/_template/build.py`：

```python
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
```

创建 `eras/_template/src/notes/README.md`：

```markdown
# （改我：时代名）· 设计笔记

> 本目录的 `.md` 是源，`notes/` 里的 `.html` 是产物。改正文改这里，然后跑 `python build.py`。

## 目录约定

| 文件 | 内容 |
|---|---|
| `01-美学考据.md` | 谱系、代表作、形式法则 |
| `02-设计系统.md` | 色板 / 字体 / 网格 / 动效 / 对比度实测 |
| `03-素材与授权.md` | 素材来源、许可证、验证方式 |
| `04-技术配方.md` | 可复制 CSS/SVG/JS + 坑 + 兼容性 |
```

创建 `eras/_template/src/notes/01-美学考据.md`：

```markdown
# （改我：美学考据）

> 一句话导语：这个时代的形式语言是什么。

## 0. 坐标系

（它从哪来、和前后时代的关系。）

## 1. 代表作

| 作品 | 作者 | 年份 | 为什么重要 |
|---|---|---|---|
|  |  |  |  |

## 2. 形式法则

1. 
2. 
3. 

## 3. 来源

- 
```

创建 `eras/_template/src/notes/doc.css`：

```css
.doc { background: var(--era-paper, #f7f5f0); color: var(--era-ink, #111); }
.doc__bar { display: flex; gap: 1rem; padding: 1rem 1.25rem; border-bottom: 2px solid currentColor; }
.doc__bar a { color: inherit; }
.doc__body, .doc__index { max-width: 46rem; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
.doc__body h1, .doc__body h2, .doc__body h3 { line-height: 1.15; }
.doc__body table { border-collapse: collapse; width: 100%; display: block; overflow-x: auto; }
.doc__body th, .doc__body td { border: 1px solid currentColor; padding: .4rem .6rem; text-align: left; }
.doc__body pre { overflow-x: auto; padding: 1rem; border: 1px solid currentColor; }
.doc__body code { font-family: ui-monospace, Consolas, monospace; }
.doc__index ul { list-style: none; padding: 0; }
.doc__index li { border-bottom: 1px solid currentColor; }
.doc__index a { display: block; padding: .8rem 0; color: inherit; }
```

创建 `eras/_template/assets/.gitkeep`（空文件）。

创建 `eras/_template/AGENTS.md`：

```markdown
# （改我：时代名）· 时代包

> 这是 `eras/_template/` 的说明样板。复制整个目录为 `eras/<slug>/`，然后：
> 1. 改 `era.json` 的 slug（必须等于目录名）/ order / name / years / summary；
> 2. 改本文件标题；
> 3. 跑 `python tools/build_all.py`，看门里出现这个时代。
> 做这个时代时只需要读三份文件：`docs/ERA-CONTRACT.md`、本文件、`src/notes/` 里的源。

## 目录

| 路径 | 是什么 | 手改吗 |
|---|---|---|
| `era.json` | 元数据 + 构建配置 | ✅ |
| `index.html` | 时代入口（整页画布） | ✅ |
| `era.css` / `era.js` | 这个时代自己的样式与脚本 | ✅ |
| `entry.css` | 到场节拍（可选） | ✅ |
| `assets/` | 素材 | ✅ |
| `src/notes/*.md` | 笔记源 | ✅ |
| `notes/*.html` | 产物 | ❌ 构建会覆盖 |
| `build.py` | 构建脚本 | ✅（一般不用动） |

## 规矩

1. 本目录只能引用本目录内的文件；不得引用其他时代、`../../core/`、`../../tools/`。
2. 站内链接用相对路径，不要以 `/` 开头。
3. 字体只在本时代页面加载。
4. 产物目录只放 `.html` `.css` `.js` 和图片。

## 验收

```bash
python tools/build_all.py          # 构建 + 体检
python -m unittest discover -s tools/tests -t tools -v
powershell -ExecutionPolicy Bypass -File tools/verify/static-check.ps1 -Dir eras/<slug> -Html index.html -Css era.css -Js era.js
```
```

创建 `docs/ERA-CONTRACT.md`：

```markdown
# 时代契约（ERA-CONTRACT）

> 做任何一个新美学时代，只读这份 + `eras/_template/AGENTS.md` + 本时代的 `src/`。
> 设计依据：`docs/superpowers/specs/2026-11-02-era-architecture-design.md`

## 1. 一个时代包是什么

`eras/<slug>/` 一个目录，自包含：页面、样式、脚本、素材、Markdown 源、构建脚本、说明。
时代之间零共享样式 / 零共享脚本 / 零相互引用。

## 2. 必需文件

| 文件 | 说明 |
|---|---|
| `era.json` | 元数据，见 §3 |
| `index.html` | 时代入口 |
| `build.py` | 构建脚本（从 `_template` 复制） |
| `AGENTS.md` | 本时代的工作说明 |

可选：`era.css`、`era.js`、`entry.css`、`assets/`、`src/`、`notes/`、`motion/`、`verify/`。

## 3. `era.json`

| 字段 | 必需 | 说明 |
|---|---|---|
| `slug` | 是 | `^[a-z0-9]+(-[a-z0-9]+)*$`，等于目录名；发布后不可改 |
| `order` | 是 | 整数，全局唯一，决定门上的顺序 |
| `name` | 是 | 门上的名称 |
| `years` | 是 | 展示用年代 |
| `summary` | 是 | ≤60 字，门上的副标题 |
| `status` | 是 | `published` / `draft`；draft 不进门、不进 sitemap |
| `notes` | 否 | `{ "dir": "notes", "label": "设计笔记" }` |
| `motion` | 否 | `{ "entry": "motion/index.html", "label": "动效原型" }` |
| `arrival` | 否 | 到场节拍 CSS，默认 `entry.css` |
| `legacy` | 否 | 旧路径前缀数组，如 `["/notes/"]`，构建生成 301 |
| `build` | 否 | 构建脚本，默认 `build.py` |

## 4. URL

| 内容 | 地址 |
|---|---|
| 门 | `/` |
| 时代入口 | `/<slug>/` |
| 笔记 | `/<slug>/notes/…` |
| 动效 | `/<slug>/motion/…` |
| 素材 | `/<slug>/assets/…` |

- 站内链接一律相对路径，禁止以 `/` 开头。
- 旧地址：`legacy` 里每条前缀 `p` 生成 `/p → /<slug>/p` 与 `/p/* → /<slug>/p/:splat` 的 301。

## 5. 边界（构建会强制检查）

1. 时代内文件不得引用其他时代、`core/` 内部实现、根 `tools/`。
2. 根层不得出现时代专属文案、色值、字体名。
3. 每个时代自带字体声明只在本时代页面生效。
4. 产物目录只含 `.html` `.css` `.js` 和图片。
5. 违反任一条，`python tools/build_all.py` 失败并指出文件。

## 6. 开工清单

```bash
cp -r eras/_template eras/<slug>
# 改 era.json（slug/order/name/years/summary/status）
# 改 AGENTS.md 标题、index.html、era.css
python tools/build_all.py
```

## 7. 学习美学的工作流（占位，下一步单独出规格）

0 立项 → 1 考据 → 2 设计系统 → 3 素材与授权 → 4 技术配方 → 5 页面实现 → 6 验证 → 7 交付。
每阶段产物路径与验收门槛见设计文档第 8 节。
```

- [ ] **Step 2: 验证脚手架能独立构建**

Run: `python eras/_template/build.py`
Expected: 输出 `[OK] notes/README.html`、`[OK] notes/01-美学考据.html`、`[OK] notes/index.html + notes/doc.css`。

Run: `git status --short`
Expected: 只有 `eras/_template/**` 与 `docs/ERA-CONTRACT.md` 是新增。

- [ ] **Step 3: 验证 build_all 会跳过 `_template`**

Run: `python tools/build_all.py`
Expected: 退出码 0，`core/eras.json` 里 `eras` 为空数组。

- [ ] **Step 4: 提交**

```bash
git add eras/_template docs/ERA-CONTRACT.md
git commit -m "feat(eras): 时代脚手架 _template + 契约文档"
```

---

## Task 5: 迁移苏联时代（搬家，不改视觉）

**Files:**
- Move: `index.html` → `eras/soviet-1923/index.html`
- Move: `press.css` → `eras/soviet-1923/era.css`
- Move: `press.js` → `eras/soviet-1923/era.js`
- Move: `assets/` → `eras/soviet-1923/assets/`
- Move: `notes/` → `eras/soviet-1923/notes/`
- Move: `motion/` → `eras/soviet-1923/motion/`
- Move: `src/notes/` → `eras/soviet-1923/src/notes/`
- Move: `src/motion/` → `eras/soviet-1923/src/motion/`
- Move: `src/verify/` → `tools/verify/`
- Move: `src/tools/render-frames.cjs` → `tools/render-frames.cjs`
- Create: `eras/soviet-1923/era.json`
- Create: `eras/soviet-1923/build.py`
- Create: `eras/soviet-1923/AGENTS.md`
- Create: 根 `index.html`（临时跳转页，Task 6 会被生成的门覆盖）
- Modify: `eras/soviet-1923/index.html`（css/js 引用）
- Modify: `eras/soviet-1923/motion/index.html`（3 条绝对链接改相对）
- Modify: `eras/soviet-1923/src/notes/build.py`（og:url）
- Modify: `构建.bat`（改为调 `tools/build_all.py`）

**Interfaces:**
- Consumes: Task 1–4 的全部产物。
- Produces: `eras/soviet-1923/` 完整时代包；旧 URL 前缀 `/notes/`、`/motion/`、`/assets/` 写入 `legacy`；`tools/verify/` 与 `tools/render-frames.cjs` 就位。

**关键事实（先记下来，避免迁移后踩坑）：**
- `notes/build.py` 和 `motion/build.py` 的 `default_out()` 会从脚本位置向上两级找 `index.html` + `notes/` 来判断仓库根。脚本移到 `eras/soviet-1923/src/<name>/` 后，上两级正好是 `eras/soviet-1923/`，判定仍然正确；`build.py` 仍显式传 `--out` 更稳。
- 已核实：`notes/` 产物里的链接全是相对路径，整体搬家后仍然有效。
- 已核实：`motion/index.html` 里有 3 条以 `/` 开头的导航链接（`/`、`/notes/`、`/motion/README.html`），必须改相对，否则构建体检的隔离检查会报错。

- [ ] **Step 1: 记录迁移前基线**

Run:

```powershell
git rev-parse HEAD
Get-ChildItem notes,motion -Recurse -File -Include *.html,*.css |
  Get-FileHash | Sort-Object Path |
  ForEach-Object { "$($_.Hash.Substring(0,12))  $($_.Path.Replace('C:\Users\23077\Desktop\work_place\网页制作工作区\',''))" } |
  Set-Content "$env:TEMP\l4e-before.txt"
```

Expected: 生成 `%TEMP%\l4e-before.txt`，供 Step 9 对比。

- [ ] **Step 2: 建目录并 `git mv` 搬家**

```powershell
New-Item -ItemType Directory -Force eras\soviet-1923 | Out-Null
New-Item -ItemType Directory -Force eras\soviet-1923\src | Out-Null
git mv index.html eras/soviet-1923/index.html
git mv press.css eras/soviet-1923/era.css
git mv press.js eras/soviet-1923/era.js
git mv assets eras/soviet-1923/assets
git mv notes eras/soviet-1923/notes
git mv motion eras/soviet-1923/motion
git mv src/notes eras/soviet-1923/src/notes
git mv src/motion eras/soviet-1923/src/motion
git mv src/verify tools/verify
git mv src/tools/render-frames.cjs tools/render-frames.cjs
git mv src/README.md eras/soviet-1923/src/README.md
```

- [ ] **Step 3: 清理旧 `src/` 残留**

```powershell
git status --short | Select-Object -First 40
Get-ChildItem src -Force -ErrorAction SilentlyContinue
```

若有残留文件（应为空或只剩 `__pycache__`），确认后 `git rm -r src`；目录不存在就跳过。

- [ ] **Step 4: 改入口页引用**

`eras/soviet-1923/index.html`：

```diff
-<link rel="stylesheet" href="press.css">
+<link rel="stylesheet" href="era.css">
...
-<script src="press.js"></script>
+<script src="era.js"></script>
```

- [ ] **Step 5: 改动效原型的 3 条绝对链接**

`eras/soviet-1923/motion/index.html`：

```diff
-<a href="/">← 回报纸首页</a>
-<a href="/notes/">设计笔记</a>
-<a href="/motion/README.html">视频设计 · 3 篇</a>
+<a href="../">← 回报纸首页</a>
+<a href="../notes/index.html">设计笔记</a>
+<a href="README.html">视频设计 · 3 篇</a>
```

- [ ] **Step 6: 改笔记首页的 og:url**

`eras/soviet-1923/src/notes/build.py`：

```diff
-<meta property="og:url" content="https://look4end.com/">
+<meta property="og:url" content="https://look4end.com/soviet-1923/notes/">
```

- [ ] **Step 7: 建 era.json、构建入口、时代说明**

创建 `eras/soviet-1923/era.json`：

```json
{
  "slug": "soviet-1923",
  "order": 10,
  "name": "苏联构成主义",
  "years": "1919–1925",
  "summary": "红黑白三色、几何原语、硬边斜切——把海报当作论证。",
  "status": "published",
  "notes": { "dir": "notes", "label": "设计笔记" },
  "motion": { "entry": "motion/index.html", "label": "动效原型" },
  "legacy": ["/notes/", "/motion/", "/assets/"]
}
```

创建 `eras/soviet-1923/build.py`：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""苏联时代构建：设计笔记 + 动效文档。产物写进本目录的 notes/ 与 motion/（不动 motion/index.html）。"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(script, out):
    path = os.path.join(ROOT, script)
    print("  → %s" % script)
    proc = subprocess.run(
        [sys.executable, path, "--out", os.path.join(ROOT, out)],
        cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(proc.returncode)


run(os.path.join("src", "notes", "build.py"), "notes")
run(os.path.join("src", "motion", "build.py"), "motion")
```

创建 `eras/soviet-1923/AGENTS.md`：

```markdown
# 苏联构成主义（soviet-1923）· 时代包

> 做这个时代的内容时只需要读：本文件 + `docs/ERA-CONTRACT.md` + 本目录的 `src/`。
> 别读别的时代，别读根层实现。

## 这个时代是什么

《ЛЕФ》构成主义报纸风格的交互原型：报纸首页 → 三张海报（КЛИН / КНИГИ / БАШНЯ）→ 文章抽屉。
红黑白三色、几何原语、硬边斜切、斜轴构图。

## 目录

| 路径 | 是什么 | 手改 |
|---|---|---|
| `era.json` | 元数据 | ✅ |
| `index.html` | 报纸首页 | ✅ |
| `era.css` / `era.js` | 首页样式与两级状态机 | ✅ |
| `src/notes/*.md` | 11 篇设计笔记的源 | ✅ |
| `src/motion/*.md` | 3 篇动效经验的源 | ✅ |
| `notes/` | 笔记产物 | ❌ |
| `motion/index.html` | 动效原型（手写单文件） | ✅ |
| `motion/*.html` | 动效文档产物 | ❌ |
| `build.py` | 构建入口 | ✅（一般不动） |

## 已知事实（别重新踩）

- 根层历史：这个包以前就是站点根目录，`press.css/press.js` 现在叫 `era.css/era.js`。
- 笔记产物里的链接全相对，整体搬家有效；别把链接改成 `/` 开头。
- 动效原型里 `window.__seek(t)` 与 `window.__state` 是出片脚本的钩子，别删。
- `motion/build.py` 的 `LINK_MAP` 把源里的 `../constructivism/...` 映射到 `../notes/...`，改文档时别破坏。
- 页面用 Google Fonts；断网会退化，版面不塌，这是有意保留的。

## 验收

```bash
python eras/soviet-1923/build.py
python tools/build_all.py
powershell -ExecutionPolicy Bypass -File tools/verify/static-check.ps1 -Dir eras/soviet-1923 -Html index.html -Css era.css -Js era.js
powershell -ExecutionPolicy Bypass -File tools/verify/flow-test.ps1 -Page eras/soviet-1923/index.html -TestScript tools/verify/example-flow-test.js
```
```

- [ ] **Step 8: 根临时跳转页（Task 6 会被覆盖）**

创建根 `index.html`：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="0; url=/soviet-1923/">
<title>Look4End · 正在进入</title>
</head>
<body>
<p><a href="/soviet-1923/">进入「苏联构成主义」 →</a></p>
</body>
</html>
```

- [ ] **Step 9: 重建并对比产物**

Run: `python eras/soviet-1923/build.py`
Expected: 笔记 11 页 + 动效 3 页全部生成，退出码 0。

Run:

```powershell
Get-ChildItem eras\soviet-1923\notes,eras\soviet-1923\motion -Recurse -File -Include *.html,*.css |
  Get-FileHash | Sort-Object Path |
  ForEach-Object { "$($_.Hash.Substring(0,12))  $($_.Path.Replace('C:\Users\23077\Desktop\work_place\网页制作工作区\eras\soviet-1923\',''))" } |
  Set-Content "$env:TEMP\l4e-after.txt"
Compare-Object (Get-Content "$env:TEMP\l4e-before.txt") (Get-Content "$env:TEMP\l4e-after.txt")
```

Expected: 只应出现 `notes/index.html`（og:url 变化）与 `motion/index.html`（3 条链接变化）的差异；其余文件哈希一致。若出现别的差异，先查清楚再继续。

Run: `git status --short`
Expected: 只有预期内的重命名 + 修改（`eras/soviet-1923/index.html`、`motion/index.html`、`src/notes/build.py`）+ 新增（`era.json`、`build.py`、`AGENTS.md`、根临时 `index.html`）。

- [ ] **Step 10: 跑构建与体检**

Run: `python tools/build_all.py`
Expected: 退出码 0；`core/eras.json` 里有 `soviet-1923`；门里出现「苏联构成主义」；`_redirects` 有 `/notes/*`、`/motion/*`、`/assets/*` 三条 301。

> 注意：这一步会把根 `index.html` 覆盖成门。为了让 P1 阶段线上不出现 404，Step 12 提交前会把临时跳转页写回去；生成的门等 Task 6 再正式提交。

- [ ] **Step 11: 更新 `构建.bat`（本机文件，被 gitignore）**

```bat
@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo   ==========================================
echo      网页制作工作区 · 重新构建
echo   ==========================================
echo.
python tools\build_all.py
if errorlevel 1 goto failed
echo.
echo   完成。本地双击 index.html 看门，双击 eras\soviet-1923\index.html 看报纸。
echo.
pause
exit /b 0
:failed
echo.
echo   [失败] 把上面的报错发给我。
echo.
pause
exit /b 1
```

- [ ] **Step 12: 提交（只提交搬家；生成物留给 Task 6）**

先把根 `index.html` 写回临时跳转页（Step 10 被门覆盖了）：

```powershell
@'
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="0; url=/soviet-1923/">
<title>Look4End · 正在进入</title>
</head>
<body><p><a href="/soviet-1923/">进入「苏联构成主义」 →</a></p></body>
</html>
'@ | Set-Content -Path index.html -Encoding UTF8
git add eras tools/verify tools/render-frames.cjs index.html
git commit -m "refactor(eras): 苏联内容整体迁入 eras/soviet-1923（搬家不改视觉）"
```

Expected: 提交后 `git status` 里只剩 Task 6 的四个生成物（`core/eras.json`、`sitemap.xml`、`_redirects` 未跟踪）与 `index.html` 待覆盖状态。

---

## Task 6: 根层切换为时间门 + 生成物入库

**Files:**
- Generated: `index.html`、`core/eras.json`、`sitemap.xml`、`_redirects`
- Modify: `.gitignore`（补 `_shots/` 与 `__pycache__/`）
- Modify: `robots.txt`（确认 sitemap 行仍指向 `/sitemap.xml`）

**Interfaces:**
- Consumes: Task 5 的时代包。
- Produces: 线上 `/` = 时间门；旧地址 301；sitemap 自动生成。

- [ ] **Step 1: 生成并检查门**

Run: `python tools/build_all.py`
Expected: 退出码 0；输出「体检通过：1 个时代，N 个页面」。

Run:

```powershell
Select-String -Path index.html -Pattern '<script','fonts.googleapis','<img'
```

Expected: 无输出（门里没有脚本 / 外链字体 / 图片）。

Run: `Get-Content core\eras.json`
Expected: `eras` 数组只有 `soviet-1923`。

Run: `Get-Content _redirects`
Expected: 六条规则（三条精确 + 三条 splat），都是 `301`。

- [ ] **Step 2: 本地目视 + 链接**

在浏览器打开 `index.html`，点「苏联构成主义」按钮，应进入报纸页；报纸内「设计笔记 · 11 篇」「视频设计」入口可点；ESC 逐级返回正常。

Run: `python -m unittest discover -s tools/tests -t tools -v`
Expected: 全部 PASS。

- [ ] **Step 3: 补 `.gitignore`**

在 `.gitignore` 末尾追加：

```
# 构建出来的临时截图 / Python 缓存
_shots/
__pycache__/
*.pyc
```

- [ ] **Step 4: 提交**

```bash
git add index.html core/eras.json sitemap.xml _redirects .gitignore
git commit -m "feat(gate): 根路径切换为时间门，sitemap/redirects 改由构建生成"
```

---

## Task 7: 验证脚本参数化与一键验收

**Files:**
- Move/keep: `tools/verify/static-check.ps1`、`flow-test.ps1`、`shot.ps1`、`example-flow-test.js`、`route-test.js`（Task 5 已搬过来）
- Create: `tools/verify/run_all.py`
- Modify: `tools/verify/static-check.ps1`（`-Css` / `-Js` 传空字符串时跳过，不算失败）
- Modify: `tools/verify/route-test.js`（注释里的路径示例）

**Interfaces:**
- Produces: `python tools/verify/run_all.py [--browser]`，退出码 0/1；一条命令覆盖构建、单测、静态检查、路由测试。

- [ ] **Step 1: 让 static-check 支持跳过可选的 CSS / JS**

`tools/verify/static-check.ps1` 第 98 行与第 119 行改成：

```diff
-} else { Fail "找不到 $Css" }
+} elseif ($Css) { Fail "找不到 $Css" }
...
-} else { Fail "找不到 $Js" }
+} elseif ($Js) { Fail "找不到 $Js" }
```

并在开头参数说明里补一句：`-Css` / `-Js` 传空字符串表示该时代没有这两个文件，跳过检查。

- [ ] **Step 2: 写 `run_all.py`**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_all.py —— 一条命令跑全站验收：构建 → 单测 → 静态检查 → 路由测试（可选浏览器链路）"""
import argparse
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VERIFY = os.path.dirname(os.path.abspath(__file__))


def run(name, cmd, cwd=REPO):
    print("\n=== %s" % name)
    proc = subprocess.run(cmd, cwd=cwd)
    if proc.returncode != 0:
        print("  [XX] %s 失败（退出码 %d）" % (name, proc.returncode), file=sys.stderr)
        return False
    print("  [OK] %s" % name)
    return True


def eras(root):
    base = os.path.join(root, "eras")
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        meta = os.path.join(path, "era.json")
        if name.startswith("_") or not os.path.isfile(meta):
            continue
        with open(meta, encoding="utf-8") as fh:
            yield path, json.load(fh)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--browser", action="store_true", help="额外跑无头浏览器的交互链路与截图")
    args = ap.parse_args()
    ps = os.environ.get("SystemRoot", r"C:\Windows") + r"\System32\WindowsPowerShell\v1.0\powershell.exe"
    ok = True

    ok &= run("构建 + 体检", [sys.executable, os.path.join(REPO, "tools", "build_all.py")])
    ok &= run("纯逻辑单测", [sys.executable, "-m", "unittest", "discover", "-s", "tools/tests", "-t", "tools"])
    ok &= run("路由单元测试", ["node", os.path.join(VERIFY, "route-test.js")])

    for era_dir, meta in eras(REPO):
        css = os.path.join(era_dir, "era.css")
        js = os.path.join(era_dir, "era.js")
        ok &= run(
            "静态检查 · %s" % meta["slug"],
            [ps, "-ExecutionPolicy", "Bypass", "-File", os.path.join(VERIFY, "static-check.ps1"),
             "-Dir", era_dir, "-Html", "index.html",
             "-Css", css if os.path.isfile(css) else "",
             "-Js", js if os.path.isfile(js) else ""],
        )

    if args.browser:
        soviet = os.path.join(REPO, "eras", "soviet-1923")
        ok &= run(
            "交互链路 · soviet-1923",
            [ps, "-ExecutionPolicy", "Bypass", "-File", os.path.join(VERIFY, "flow-test.ps1"),
             "-Page", os.path.join(soviet, "index.html"),
             "-TestScript", os.path.join(VERIFY, "example-flow-test.js")],
        )
        ok &= run(
            "多状态截图 · soviet-1923",
            [ps, "-ExecutionPolicy", "Bypass", "-File", os.path.join(VERIFY, "shot.ps1"),
             "-Page", os.path.join(soviet, "index.html"), "-Out", os.path.join(REPO, "_shots")],
        )

    print("\n%s" % ("全部通过" if ok else "有失败项"))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 跑一次（无浏览器）**

Run: `python tools/verify/run_all.py`
Expected: 构建 / 单测 / 路由 / 静态检查全绿，最后输出「全部通过」。

- [ ] **Step 4: 跑一次（含浏览器）**

Run: `python tools/verify/run_all.py --browser`
Expected: 额外两项绿；检查 `_shots/` 里截图。

- [ ] **Step 5: 提交**

```bash
git add tools/verify/run_all.py tools/verify/*.ps1 tools/verify/*.js
git commit -m "chore(verify): 验证脚本参数化 + 一键验收 run_all"
```

---

## Task 8: 文档分层（根 AGENTS / WORKFLOW / README / 时代说明）

**Files:**
- Modify: `AGENTS.md`（本机文件，被 gitignore）→ 重写为根层入口
- Modify: `WORKFLOW.md`
- Modify: `README.md`
- Modify: `eras/soviet-1923/src/README.md`
- Modify: `eras/_template/AGENTS.md`（若 Task 4 的内容需要按最终命令微调）

**Interfaces:**
- Produces: 新会话读 `AGENTS.md` + `docs/ERA-CONTRACT.md` 就能接手；做新时代不需要读苏联包。

- [ ] **Step 1: 重写根 `AGENTS.md`（≤80 行）**

```markdown
# 网页制作工作区

**这里是 look4end.com 的工作副本。** 站点结构 = 时间门 + 时代包。

> 给 AI / 协作者的入口。人看的导航在 [`README.md`](./README.md)。

## 一、目录

```
index.html                ← 生成：时间门（不手改）
core/gate.css             门的基础样式
core/eras.json            ← 生成：注册表（不手改）
eras/<slug>/              一个时代包（自包含）
  era.json  index.html  era.css  era.js  entry.css  assets/  src/  notes/  motion/  AGENTS.md
eras/_template/           新时代脚手架（复制即开工）
tools/build_all.py        构建调度：跑各时代构建 → 生成门/sitemap/redirects → 体检
tools/era_lib.py          规则层（纯函数）
tools/verify/             验证脚本 + run_all.py
tools/tests/              纯逻辑单测
docs/ERA-CONTRACT.md      时代契约（唯一的跨时代文档）
docs/superpowers/         设计 / 计划文档
```

## 二、三条命令

```bash
python tools/build_all.py                 # 构建 + 体检
python tools/verify/run_all.py            # 全站验收（加 --browser 跑交互与截图）
git add -A && git commit -m "说明" && git push   # 或双击 publish.bat
```

## 三、改哪里

| 想改什么 | 改哪儿 |
|---|---|
| 某个时代的页面 / 样式 / 笔记 | `eras/<slug>/` 里对应文件 |
| 加一个新时代 | 复制 `eras/_template` → 改 `era.json` → 写页面 → 跑构建 |
| 门的样子 / 时代排序 | `tools/templates/gate.html`、`core/gate.css`、各 `era.json` 的 `order` |
| 构建规则 / 体检项 | `tools/era_lib.py`、`tools/build_all.py` |
| 跨时代规则 | `docs/ERA-CONTRACT.md`（先改契约，再改实现） |

## 四、铁律

1. `index.html`、`core/eras.json`、`sitemap.xml`、`_redirects`、`eras/*/notes/`、`eras/*/motion/*.html` 是**产物**，不要手改。
2. 时代之间零引用；时代内不得引用 `core/` 与 `tools/`。
3. 站内链接一律相对路径。
4. 改完必须 `python tools/build_all.py` 通过；连续两次构建 `git diff` 必须为空。
5. 发布 = `git push` → Cloudflare Pages 自动重建（约 30 秒）。

## 五、接手时怎么开始

1. 读本文件 → 读 [`docs/ERA-CONTRACT.md`](./docs/ERA-CONTRACT.md)
2. `git status` 确认干净
3. `python tools/build_all.py` 确认能构建
4. 再动内容

## 六、下一步（未完成）

- 「学习美学的工作流」规格：`docs/superpowers/specs/` 下另立文档
- 第二个时代（暂定 `gaslight-1891`）：只按契约 + 模板开工
```

- [ ] **Step 2: 重写 `WORKFLOW.md`（保留「给接手的人」口吻）**

至少包含：站点三层结构（门 / 苏联时代 / 未来时代）、源与产物对照表、三条命令、发布链、已核实的技术事实（Google Fonts 依赖、`.html` 308、`.bat` 中文注释坑、域名 DNS 在 Cloudflare）、5 个阶段的重构历史一段、以及「新增时代只读 3 份文件」。

- [ ] **Step 3: 更新 `README.md`**

把「项目结构」一节替换为新目录树（门 + eras + tools + docs），把「改内容」一节改成「改某个时代」与「加一个时代」两条路径，其余（发布、部署信息）保留。

- [ ] **Step 4: 更新 `eras/soviet-1923/src/README.md`**

把 `../WORKFLOW.md` 改成 `../../../WORKFLOW.md`（相对新位置），目录说明改成「本时代的源与构建脚本」。

- [ ] **Step 5: 检查文档里的路径**

Run:

```powershell
Select-String -Path AGENTS.md,README.md,WORKFLOW.md,docs\ERA-CONTRACT.md -Pattern "press\.css|press\.js|src/verify|src/tools|^notes/|^motion/" 
```

Expected: 只应该出现在「历史 / 迁移」语境里，不能作为当前操作路径。

- [ ] **Step 6: 提交**

```bash
git add README.md WORKFLOW.md eras/soviet-1923/src/README.md eras/_template/AGENTS.md
git commit -m "docs: 文档分层到根层 / 时代包 / 契约三层"
```

---

## Task 9: 清理、终验与上线

**Files:**
- Modify: `.gitignore`（如还有遗漏）
- 本机动作（不在仓库内）：归档旧克隆副本

- [ ] **Step 1: 归档本机第二份克隆**

先确认路径再动：

```powershell
$old = "C:\Users\23077\dev\look4end-site"
if (Test-Path $old) { Get-ChildItem $old -Force | Select-Object Name | Out-String }
```

确认是那份旧克隆后：

```powershell
Rename-Item $old "look4end-site.archived-2026-11-02"
```

Expected: 目录改名成功；以后只在 `网页制作工作区` 里改。

- [ ] **Step 2: 终验（全部命令）**

```bash
python tools/build_all.py
python tools/build_all.py
git diff --exit-code
python -m unittest discover -s tools/tests -t tools -v
python tools/verify/run_all.py
python tools/verify/run_all.py --browser
```

Expected: 全绿；第二次构建后 `git diff` 为空；浏览器链路 7 项全 OK；截图逐张看过。

- [ ] **Step 3: 本地目视清单**

- 门：1 个时代、可点、无脚本、移动端不挤
- 苏联报纸：三张海报可进、抽屉可开、ESC 逐级返回、转场层归位
- 动效原型：空格播放、循环点无跳
- 笔记 11 篇：目录、翻页、样式正常
- 断网测试：字体退化成系统字体，版面不塌

- [ ] **Step 4: 提交收尾**

```bash
git status --short
git add -A
git commit -m "chore: 收尾——.gitignore 补全与终验记录"
```

- [ ] **Step 5: 上线（需要人工确认）**

> 这一步会改变线上站点。执行前向用户确认，然后：

```bash
git push
```

Expected: GitHub 收到推送；Cloudflare Pages 约 30 秒后重建。

- [ ] **Step 6: 线上抽查**

```powershell
$urls = @(
  "https://look4end.com/",
  "https://look4end.com/soviet-1923/",
  "https://look4end.com/soviet-1923/notes/",
  "https://look4end.com/soviet-1923/motion/",
  "https://look4end.com/notes/01-%E7%BE%8E%E5%AD%A6%E8%B0%B1%E7%B3%BB%E4%B8%8E%E5%BD%A2%E5%BC%8F%E6%B3%95%E5%88%99",
  "https://look4end.com/motion/",
  "https://look4end.com/assets/lissitzky-wedge.jpg",
  "https://look4end.com/sitemap.xml"
)
foreach ($u in $urls) {
  try { $r = Invoke-WebRequest $u -MaximumRedirection 0 -UseBasicParsing -ErrorAction Stop; "{0}  {1}" -f $r.StatusCode, $u }
  catch { "{0}  {1}" -f $_.Exception.Response.StatusCode.value__, $u }
}
```

Expected：
- 前四个 `200`
- `/notes/01-…`、`/motion/`、`/assets/…` 返回 `301` 且 `Location` 指向 `/soviet-1923/…`
- `sitemap.xml` `200`，内容里没有 `/notes/` 旧路径

- [ ] **Step 7: 更新交接状态**

在 `WORKFLOW.md` 末尾写一段「2026-11-02 重构后实测」：构建、链接、tests、线上抽查结果。提交。

---

## 自审记录（写完计划后自查）

- **规格覆盖**：设计文档 §4 架构 → Task 1–3；§5 目录 → Task 4/5；§6 契约 → Task 4（ERA-CONTRACT）与 `check_isolation`；§7 门 → Task 2；§9 构建 → Task 3；§10 验证 → Task 7；§11 迁移 → Task 5/6；§12 风险（旧克隆、公开面）→ Task 9。
- **占位符扫描**：无 TBD；`（改我：…）` 是脚手架模板的显式占位，不是计划缺内容。
- **类型一致性**：`load_eras` 返回顺序与 `render_registry` 字段名一致；`render_gate` 的占位名与 `gate.html` 一致；`check_*` 均返回 `list[str]`。
- **已知取舍**：本次不迁移「学习美学工作流」的规格内容（设计文档 §8 只留骨架），它按用户决定作为重构后的下一条线单独出规格。
- **已知取舍**：苏联时代本次不加 `entry.css`（到场节拍），避免迁移引入视觉变化；`arrival` 字段留给模板演示。
