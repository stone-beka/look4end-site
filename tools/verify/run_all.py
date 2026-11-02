#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""run_all.py —— 一条命令跑全站验收：构建 → 单测 → 静态检查 → 路由测试（可选浏览器链路）"""
import argparse
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VERIFY = os.path.dirname(os.path.abspath(__file__))
PS = shutil.which("powershell") or os.path.join(
    os.environ.get("SystemRoot", r"C:\Windows"),
    r"System32\WindowsPowerShell\v1.0\powershell.exe",
)
NODE = shutil.which("node") or "node"

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


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
    ok = True

    ok &= run("构建 + 体检", [sys.executable, os.path.join(REPO, "tools", "build_all.py")])
    ok &= run("纯逻辑单测", [sys.executable, "-m", "unittest", "discover", "-s", "tools/tests", "-t", "tools"])
    ok &= run("路由单元测试", [NODE, os.path.join(VERIFY, "route-test.js")])

    for era_dir, meta in eras(REPO):
        has_css = os.path.isfile(os.path.join(era_dir, "era.css"))
        has_js = os.path.isfile(os.path.join(era_dir, "era.js"))
        ok &= run(
            "静态检查 · %s" % meta["slug"],
            [PS, "-ExecutionPolicy", "Bypass", "-File", os.path.join(VERIFY, "static-check.ps1"),
             "-Dir", era_dir, "-Html", "index.html",
             "-Css", "era.css" if has_css else "",
             "-Js", "era.js" if has_js else ""],
        )

    if args.browser:
        soviet = os.path.join(REPO, "eras", "soviet-1923")
        ok &= run(
            "交互链路 · soviet-1923",
            [PS, "-ExecutionPolicy", "Bypass", "-File", os.path.join(VERIFY, "flow-test.ps1"),
             "-Page", os.path.join(soviet, "index.html"),
             "-TestScript", os.path.join(VERIFY, "example-flow-test.js")],
        )
        ok &= run(
            "多状态截图 · soviet-1923",
            [PS, "-ExecutionPolicy", "Bypass", "-File", os.path.join(VERIFY, "shot.ps1"),
             "-Page", os.path.join(soviet, "index.html"), "-Out", os.path.join(REPO, "_shots")],
        )

    print("\n%s" % ("全部通过" if ok else "有失败项"))
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
