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

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTRO = "这里按时代陈列视觉美学。每个时代都是独立的世界，页面、字体、动效互不共享。"
LINK_RE = re.compile(r'(?:href|src)="([^"]+)"')
EXTERNAL = ("http://", "https://", "mailto:", "data:", "javascript:", "//", "#")
PRODUCT_EXTS = {
    ".html", ".css", ".js", ".png", ".jpg", ".jpeg", ".svg",
    ".webp", ".gif", ".ico", ".woff", ".woff2",
}


def run_era_build(era):
    script = era.get("build", "build.py")
    path = os.path.join(era["_dir"], script)
    if not os.path.isfile(path):
        raise SystemExit("[%s] 缺少构建脚本 %s" % (era["slug"], script))
    print("── 构建 %s" % era["slug"])
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, path], cwd=era["_dir"], env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr.rstrip(), file=sys.stderr)
        raise SystemExit("[%s] 构建失败（退出码 %d）" % (era["slug"], proc.returncode))


def write_file(path, text, root):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("  生成 %s" % os.path.relpath(path, root))


def _refs(text):
    """只取真正的链接/资源引用：先剥注释与代码块（示例代码里的 src="x" 不能算断链）。"""
    text = re.sub(r"(?is)<!--.*?-->", "", text)
    for tag in ("pre", "code", "script", "style"):
        text = re.sub(r"(?is)<%s\b.*?</%s>" % (tag, tag), "", text)
    return LINK_RE.findall(text)


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
        for target in _refs(text):
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
            for ref in _refs(text):
                if ref.startswith(EXTERNAL):
                    continue
                clean = ref.split("#", 1)[0].split("?", 1)[0]
                if not clean:
                    continue
                if clean.startswith("/"):
                    if not (clean == "/" + slug or clean.startswith("/" + slug + "/")):
                        failures.append("%s: 绝对路径 %s（应改相对路径）" % (rel, ref))
                    continue
                resolved = os.path.abspath(
                    os.path.normpath(os.path.join(os.path.dirname(path), clean))
                )
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
                        failures.append(
                            "%s: 产物里混入 %s" % (era["slug"], os.path.join(dirpath, name))
                        )
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
    write_file(os.path.join(root, "index.html"), gate, root)
    write_file(os.path.join(root, "core", "eras.json"), era_lib.render_registry(eras), root)
    write_file(os.path.join(root, "_redirects"), era_lib.render_redirects(eras), root)
    pages = era_lib.scan_pages(root)
    hidden = tuple(
        "%s/%s/" % (era_lib.ERA_ROOT, era["slug"])
        for era in eras
        if era["status"] != "published"
    )
    sitemap_pages = [p for p in pages if not (hidden and p.startswith(hidden))]
    write_file(os.path.join(root, "sitemap.xml"), era_lib.render_sitemap(sitemap_pages), root)

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
