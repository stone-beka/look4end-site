#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""era_lib.py —— 多时代站点的纯函数规则层（无副作用，便于单测）"""
import html
import json
import os
import re

SITE = "https://look4end.com"
ERA_ROOT = "eras"
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
STATUSES = ("published", "draft")
REQUIRED = ("slug", "order", "name", "years", "summary", "status")
SKIP_TOP = {"tools", "docs", "core", "node_modules", "__pycache__"}

GATE_ITEM = """      <li class="era">
        <a class="era__link" href="eras/{slug}/">
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
            lines.append("/%s /%s/%s/%s 301" % (prefix, ERA_ROOT, slug, prefix))
            lines.append("/%s/* /%s/%s/%s/:splat 301" % (prefix, ERA_ROOT, slug, prefix))
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
