import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app_inspect import cli, mcp  # noqa: E402
from fakeapple import FakeApple  # noqa: E402


def rpc(method, params=None, id=1):
    msg = {"jsonrpc": "2.0", "method": method}
    if id is not None:
        msg["id"] = id
    if params is not None:
        msg["params"] = params
    return msg


def session(*messages, get=None):
    stdin = io.StringIO("".join(json.dumps(m) + "\n" for m in messages))
    stdout = io.StringIO()
    mcp.serve(stdin, stdout, get=get or FakeApple())
    return [json.loads(line) for line in stdout.getvalue().splitlines()]


class ProtocolTests(unittest.TestCase):
    def test_initialize_echoes_supported_version(self):
        (r,) = session(rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}))
        self.assertEqual(r["result"]["protocolVersion"], "2024-11-05")
        self.assertEqual(r["result"]["serverInfo"]["name"], "app-inspect")
        self.assertIn("tools", r["result"]["capabilities"])

    def test_initialize_falls_back_to_latest(self):
        (r,) = session(rpc("initialize", {"protocolVersion": "1999-01-01"}))
        self.assertEqual(r["result"]["protocolVersion"], mcp.SUPPORTED_PROTOCOLS[0])

    def test_notification_gets_no_reply(self):
        out = session(rpc("notifications/initialized", id=None), rpc("ping", id=7))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], 7)
        self.assertEqual(out[0]["result"], {})

    def test_tools_list_has_schemas(self):
        (r,) = session(rpc("tools/list"))
        names = {t["name"] for t in r["result"]["tools"]}
        self.assertEqual(names, {"inspect_app", "compare_apps", "inspect_app_countries", "search_apps"})
        for t in r["result"]["tools"]:
            self.assertEqual(t["inputSchema"]["type"], "object")
            self.assertTrue(t["annotations"]["readOnlyHint"])

    def test_unknown_method_and_garbage(self):
        stdin = io.StringIO('not json\n' + json.dumps(rpc("nope", id=3)) + "\n")
        stdout = io.StringIO()
        mcp.serve(stdin, stdout, get=FakeApple())
        a, b = [json.loads(x) for x in stdout.getvalue().splitlines()]
        self.assertEqual(a["error"]["code"], -32700)
        self.assertEqual(b["error"]["code"], -32601)

    def test_unknown_tool_is_protocol_error(self):
        (r,) = session(rpc("tools/call", {"name": "delete_everything", "arguments": {}}))
        self.assertEqual(r["error"]["code"], -32602)


class ToolTests(unittest.TestCase):
    def call(self, name, args):
        (r,) = session(rpc("tools/call", {"name": name, "arguments": args}))
        return r["result"]

    def test_inspect_app(self):
        res = self.call("inspect_app", {"app": "1234567890", "pages": 2})
        self.assertNotIn("isError", res)
        self.assertIn("Sample Notes", res["content"][0]["text"])
        self.assertAlmostEqual(res["structuredContent"]["ratings"]["lifetime_average"], 4.8)
        self.assertIn("gap", res["structuredContent"]["ratings"])

    def test_compare_apps_two_refs(self):
        res = self.call("compare_apps", {"apps": ["1234567890", "1234567890"], "days": 14})
        self.assertEqual(len(res["structuredContent"]["apps"]), 2)

    def test_countries_labels_each_store(self):
        res = self.call("inspect_app_countries", {"app": "1234567890", "countries": ["us", "gb"]})
        names = [a["app"]["name"] for a in res["structuredContent"]["apps"]]
        self.assertEqual(names, ["Sample Notes [us]", "Sample Notes [gb]"])

    def test_search(self):
        res = self.call("search_apps", {"term": "notes"})
        self.assertIn("results", res["structuredContent"])

    def test_missing_required_argument_is_tool_error(self):
        res = self.call("inspect_app", {})
        self.assertTrue(res["isError"])
        self.assertIn("'app' is required", res["content"][0]["text"])

    def test_bad_types_are_tool_errors(self):
        self.assertTrue(self.call("compare_apps", {"apps": "1234567890"})["isError"])
        self.assertTrue(self.call("inspect_app", {"app": "1", "days": "7"})["isError"])

    def test_app_not_found_is_tool_error_not_crash(self):
        out = session(
            rpc("tools/call", {"name": "inspect_app", "arguments": {"app": "1"}}, id=1),
            rpc("ping", id=2),
            get=FakeApple(app={}),
        )
        self.assertTrue(out[0]["result"]["isError"])
        self.assertEqual(out[1]["result"], {})

    def test_network_failure_keeps_server_alive(self):
        def boom(url):
            raise OSError("network down")

        out = session(
            rpc("tools/call", {"name": "inspect_app", "arguments": {"app": "1"}}, id=1),
            rpc("ping", id=2),
            get=boom,
        )
        self.assertTrue(out[0]["result"]["isError"])
        self.assertIn("network down", out[0]["result"]["content"][0]["text"])
        self.assertEqual(out[1]["result"], {})


class SubprocessTests(unittest.TestCase):
    def test_real_stdio_roundtrip(self):
        import subprocess

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proc = subprocess.run(
            [sys.executable, "-m", "app_inspect", "mcp"],
            input=json.dumps(rpc("initialize", {"protocolVersion": "2025-06-18"})) + "\n" + json.dumps(rpc("tools/list", id=2)) + "\n",
            capture_output=True, text=True, cwd=root, timeout=30,
        )
        lines = [json.loads(x) for x in proc.stdout.splitlines()]
        self.assertEqual([m["id"] for m in lines], [1, 2])
        self.assertEqual(proc.returncode, 0)


class CliWiringTests(unittest.TestCase):
    def test_mcp_subcommand_rejects_extra_args(self):
        self.assertEqual(cli.main(["mcp", "--bogus"]), 2)


if __name__ == "__main__":
    unittest.main()
