import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_inspect import analyze, cli, fetch, render  # noqa: E402
from fakeapple import APP, NOW, FakeApple, entry  # noqa: E402


class ParseRefTests(unittest.TestCase):
    def test_numeric_id(self):
        self.assertEqual(fetch.parse_app_ref("284882215"), ("284882215", None))

    def test_id_prefix(self):
        self.assertEqual(fetch.parse_app_ref("id284882215"), ("284882215", None))

    def test_store_url_with_country(self):
        url = "https://apps.apple.com/gb/app/facebook/id284882215?uo=4"
        self.assertEqual(fetch.parse_app_ref(url), ("284882215", "gb"))

    def test_name_is_search(self):
        self.assertEqual(fetch.parse_app_ref("microsoft authenticator"), (None, None))


class FetchTests(unittest.TestCase):
    def test_reviews_paginates_dedupes_and_skips_info_entry(self):
        fake = FakeApple()
        revs = fetch.reviews("1234567890", "us", 10, get=fake)
        self.assertEqual(len(revs), 65)
        self.assertEqual(len({r["id"] for r in revs}), 65)
        # 65 entries -> page 1 full, page 2 short, so no page 3 request
        self.assertEqual(sum("/customerreviews/" in u for u in fake.urls), 2)

    def test_single_entry_object(self):
        one = entry(1, 3, "1.0", 1)
        get = lambda url: {"feed": {"entry": one}}  # noqa: E731
        revs = fetch.reviews("1", "us", 3, get=get)
        self.assertEqual(len(revs), 1)
        self.assertEqual(revs[0]["rating"], 3)

    def test_pages_clamped(self):
        fake = FakeApple(entries=[entry(i, 4, "1.0", 1) for i in range(600)])
        revs = fetch.reviews("1", "us", 99, get=fake)
        self.assertEqual(len(revs), 500)

    def test_lookup_missing_raises(self):
        with self.assertRaises(fetch.AppInspectError):
            fetch.lookup("1", "us", get=FakeApple(app={}))


class AnalyzeTests(unittest.TestCase):
    def setUp(self):
        self.revs = fetch.reviews("1234567890", "us", 10, get=FakeApple())
        self.report = analyze.inspect(APP, self.revs, now=NOW)

    def test_gap_and_level(self):
        r = self.report["ratings"]
        self.assertEqual(r["lifetime_average"], 4.8)
        self.assertEqual(r["recent_written_count"], 65)
        self.assertAlmostEqual(r["gap"], round(4.8 - r["recent_written_average"], 2))
        self.assertEqual(r["gap_level"], "big gap")

    def test_window_and_current_version(self):
        r = self.report["ratings"]
        self.assertEqual(r["last_n_days_count"], 50)  # only 3.1.0 reviews are within 30 days
        self.assertEqual(r["current_version_written_count"], 50)
        self.assertLess(r["last_n_days_average"], 2.0)

    def test_version_regression_flagged(self):
        v = {row["version"]: row for row in self.report["versions"]}
        self.assertFalse(v["3.0.0"]["regression"])
        self.assertTrue(v["3.1.0"]["regression"])
        self.assertEqual(v["3.1.0"]["vs_version"], "3.0.0")
        self.assertTrue(any("3.1.0" in f for f in self.report["flags"]))

    def test_themes(self):
        names = [t["theme"] for t in self.report["themes"]]
        for expected in ("crashes & bugs", "subscription & pricing", "data loss & sync", "update regressions"):
            self.assertIn(expected, names)
        self.assertNotIn("ads", names)
        top = self.report["themes"][0]
        self.assertTrue(top["quotes"])

    def test_verdict_mentions_regression(self):
        self.assertIn("regression", self.report["verdict"])
        self.assertIn("far less happy", self.report["verdict"])

    def test_version_sorting_is_numeric(self):
        revs = [{"rating": 5, "version": v, "updated": None} for v in ("1.10", "1.9", "1.2") for _ in range(5)]
        order = [row["version"] for row in analyze.per_version(revs)]
        self.assertEqual(order, ["1.2", "1.9", "1.10"])

    def test_in_line_and_improving(self):
        self.assertEqual(analyze.gap_level(0.3), "in line")
        self.assertEqual(analyze.gap_level(-0.8), "improving")
        self.assertEqual(analyze.gap_level(1.2), "drifting")
        self.assertEqual(analyze.gap_level(None), "unknown")

    def test_no_reviews(self):
        rep = analyze.inspect(APP, [], now=NOW)
        self.assertIsNone(rep["ratings"]["gap"])
        self.assertIn("No recent written reviews", rep["verdict"])

    def test_stale_app_flag(self):
        app = dict(APP, currentVersionReleaseDate="2024-01-01T00:00:00Z")
        rep = analyze.inspect(app, self.revs, now=NOW)
        self.assertTrue(any("No update in" in f for f in rep["flags"]))

    def test_theme_regex_avoids_common_false_positives(self):
        revs = [{"rating": 1, "title": "UI", "content": "whoever is in charge of design makes enough money", "votes": 0}]
        names = [t["theme"] for t in analyze.themes(revs)]
        self.assertNotIn("subscription & pricing", names)


class RenderTests(unittest.TestCase):
    def setUp(self):
        revs = fetch.reviews("1234567890", "us", 10, get=FakeApple())
        self.report = analyze.inspect(APP, revs, now=NOW)

    def test_text(self):
        out = render.to_text(self.report)
        self.assertIn("Sample Notes — Sample Co", out)
        self.assertIn("big gap", out)
        self.assertIn("▼ regression", out)
        self.assertIn("Verdict:", out)

    def test_markdown(self):
        out = render.to_markdown(self.report)
        self.assertIn("| Lifetime rating | 4.80★ |", out)
        self.assertIn("**Verdict:**", out)

    def test_json_roundtrip(self):
        self.assertEqual(json.loads(render.to_json(self.report))["app"]["name"], "Sample Notes")


class CliTests(unittest.TestCase):
    def run_cli(self, argv, fake=None):
        buf = io.StringIO()
        err = io.StringIO()
        old = sys.stderr
        sys.stderr = err
        try:
            code = cli.main(argv, get=fake or FakeApple(), out=buf)
        finally:
            sys.stderr = old
        return code, buf.getvalue(), err.getvalue()

    def test_inspect_json(self):
        code, out, _ = self.run_cli(["1234567890", "-f", "json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["country"], "us")

    def test_inspect_by_name_reports_match(self):
        code, out, err = self.run_cli(["sample notes"])
        self.assertEqual(code, 0)
        self.assertIn("Matched 'sample notes'", err)

    def test_country_from_url(self):
        fake = FakeApple()
        code, _, _ = self.run_cli(["https://apps.apple.com/jp/app/x/id1234567890"], fake)
        self.assertEqual(code, 0)
        self.assertTrue(all("country=jp" in u or "/jp/rss/" in u for u in fake.urls))

    def test_max_gap_exit_code(self):
        code, _, _ = self.run_cli(["1234567890", "--max-gap", "1.0"])
        self.assertEqual(code, cli.EXIT_GAP)
        code, _, _ = self.run_cli(["1234567890", "--max-gap", "4.5"])
        self.assertEqual(code, 0)

    def test_search(self):
        code, out, _ = self.run_cli(["search", "sample"])
        self.assertEqual(code, 0)
        self.assertIn("1234567890", out)

    def test_compare(self):
        code, out, _ = self.run_cli(["compare", "1234567890", "1234567890", "-f", "markdown"])
        self.assertEqual(code, 0)
        self.assertIn("| App | Lifetime |", out)

    def test_countries(self):
        code, out, _ = self.run_cli(["countries", "1234567890", "us", "jp"])
        self.assertEqual(code, 0)
        self.assertIn("[us]", out)
        self.assertIn("[jp]", out)

    def test_unknown_app_is_clean_error(self):
        code, _, err = self.run_cli(["nothing here"], FakeApple(search_results=[]))
        self.assertEqual(code, 1)
        self.assertIn("No app found", err)


class SkillFileTests(unittest.TestCase):
    def test_skill_frontmatter(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "skills", "app-inspect", "SKILL.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertTrue(text.startswith("---\n"))
        head = text.split("---")[1]
        self.assertIn("name: app-inspect", head)
        self.assertIn("description:", head)


if __name__ == "__main__":
    unittest.main()
