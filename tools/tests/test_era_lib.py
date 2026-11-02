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
        self.assertIn("/notes /eras/soviet-1923/notes 301", out)
        self.assertIn("/notes/* /eras/soviet-1923/notes/:splat 301", out)
        self.assertIn("/motion/* /eras/soviet-1923/motion/:splat 301", out)
        self.assertIn("/assets/* /eras/soviet-1923/assets/:splat 301", out)

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


if __name__ == "__main__":
    unittest.main()
