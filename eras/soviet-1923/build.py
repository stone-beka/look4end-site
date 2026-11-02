#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""苏联时代构建：设计笔记 + 动效文档。产物写进本目录的 notes/ 与 motion/（不动 motion/index.html）。"""
import os
import subprocess
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))


def run(script, out):
    path = os.path.join(ROOT, script)
    print("  → %s" % script)
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.run(
        [sys.executable, path, "--out", os.path.join(ROOT, out)],
        cwd=ROOT, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if proc.stdout:
        print(proc.stdout.rstrip())
    if proc.returncode != 0:
        if proc.stderr:
            print(proc.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(proc.returncode)


run(os.path.join("src", "notes", "build.py"), "notes")
run(os.path.join("src", "motion", "build.py"), "motion")
