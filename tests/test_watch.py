import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_inspect import cli, watch  # noqa: E402
from fakeapple import FakeApple, APP, entry  # noqa: E402


def run(args, fake):
    out = io.StringIO()
    code = cli.main(args, get=fake, out=out)
    return code, out.getvalue()


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.hist = os.path.join(self.dir, "sub", "h.jsonl")

    def test_first_run_then_unchanged(self):
        code, text = run(["watch", "1234567890", "--history", self.hist], FakeApple())
        self.assertEqual(code, 0)
        self.assertIn("First snapshot", text)
        code, text = run(["watch", "1234567890", "--history", self.hist], FakeApple())
        self.assertIn("No meaningful change", text)
        self.assertEqual(len(watch.load(self.hist)), 2)

    def test_rating_drop_and_new_version_fail_on_change(self):
        run(["watch", "1234567890", "--history", self.hist], FakeApple())
        worse = dict(APP, averageUserRating=4.5, version="3.2.0")
        code, text = run(["watch", "1234567890", "--history", self.hist, "--fail-on-change"], FakeApple(app=worse))
        self.assertEqual(code, cli.EXIT_CHANGE)
        self.assertIn("Lifetime rating fell: 4.8 -> 4.5", text)
        self.assertIn("New version: 3.1.0 -> 3.2.0", text)

    def test_no_save_and_torn_line(self):
        run(["watch", "1234567890", "--history", self.hist, "--no-save"], FakeApple())
        self.assertEqual(watch.load(self.hist), [])
        run(["watch", "1234567890", "--history", self.hist], FakeApple())
        with open(self.hist, "a") as fh:
            fh.write("{broken\n")
        self.assertEqual(len(watch.load(self.hist)), 1)

    def test_improvement_is_not_worse(self):
        a = {"lifetime_average": 4.0, "gap_level": "drifting", "regressions": []}
        b = {"lifetime_average": 4.4, "gap_level": "in line", "regressions": []}
        self.assertFalse(watch.worsened(a, b))
        self.assertTrue(watch.worsened(b, a))


if __name__ == "__main__":
    unittest.main()
