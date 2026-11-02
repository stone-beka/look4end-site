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

    def make_era(self, slug, order, status="published", broken=False):
        d = os.path.join(self.tmp, "eras", slug)
        os.makedirs(d)
        data = {"slug": slug, "order": order, "name": slug + "名", "years": "1900",
                "summary": "一句话。", "status": status}
        with open(os.path.join(d, "era.json"), "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False)
        href = "missing.html" if broken else "notes/"
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write('<!DOCTYPE html><html><body><a href="%s">笔记</a></body></html>' % href)
        os.makedirs(os.path.join(d, "notes"))
        with open(os.path.join(d, "notes", "index.html"), "w", encoding="utf-8") as fh:
            fh.write("<!DOCTYPE html><html><body>ok</body></html>")
        with open(os.path.join(d, "build.py"), "w", encoding="utf-8") as fh:
            fh.write("print('built')\n")
        return d

    def run_build(self, *extra):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, BUILD, "--root", self.tmp, *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace", env=env,
        )

    def test_happy_path(self):
        self.make_era("a-1", 10)
        self.make_era("b-2", 20)
        proc = self.run_build()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(self.tmp, "index.html"), encoding="utf-8") as fh:
            gate = fh.read()
        self.assertIn("a-1/", gate)
        self.assertIn("b-2/", gate)
        self.assertNotIn("<script", gate.lower())
        with open(os.path.join(self.tmp, "core", "eras.json"), encoding="utf-8") as fh:
            registry = json.load(fh)
        self.assertEqual([e["slug"] for e in registry["eras"]], ["a-1", "b-2"])
        with open(os.path.join(self.tmp, "sitemap.xml"), encoding="utf-8") as fh:
            sitemap = fh.read()
        self.assertIn("/a-1/", sitemap)
        self.assertIn("/a-1/notes/", sitemap)
        self.assertIn("/b-2/notes/", sitemap)
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "_redirects")))

    def test_draft_excluded(self):
        self.make_era("a-1", 10)
        self.make_era("d-9", 90, status="draft")
        proc = self.run_build()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        with open(os.path.join(self.tmp, "index.html"), encoding="utf-8") as fh:
            gate = fh.read()
        with open(os.path.join(self.tmp, "sitemap.xml"), encoding="utf-8") as fh:
            sitemap = fh.read()
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

    def test_isolation_fails_on_absolute_link(self):
        d = self.make_era("a-1", 10)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write('<!DOCTYPE html><html><body><a href="/notes/">站外</a></body></html>')
        proc = self.run_build()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("绝对路径", proc.stderr)

    def test_code_sample_links_not_checked(self):
        d = self.make_era("a-1", 10)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as fh:
            fh.write('<!DOCTYPE html><html><body><a href="notes/">笔记</a>'
                     '<pre><code>&lt;script src="press.js"&gt;&lt;/script&gt;</code></pre></body></html>')
        proc = self.run_build()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

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
