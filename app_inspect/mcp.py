"""A tiny, dependency-free Model Context Protocol (MCP) server over stdio.

Run it with ``app-inspect mcp``. It speaks newline-delimited JSON-RPC 2.0, the
MCP stdio transport, and exposes the same checks as the CLI as four read-only
tools. Nothing is written to disk and no API key is needed.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Callable, Dict, List, Optional

from . import __version__
from .fetch import AppInspectError, MAX_REVIEW_PAGES, http_get_json, search
from .render import compare_markdown, to_markdown

SUPPORTED_PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")

_APP = {"type": "string", "description": "App Store id (284882215), App Store URL, or an app name"}
_COUNTRY = {"type": "string", "description": "Two-letter storefront code, e.g. us, gb, de, jp (default: from the URL, else us)"}
_DAYS = {"type": "integer", "minimum": 1, "maximum": 365, "description": "Size of the 'recent' window in days (default 30)"}
_PAGES = {
    "type": "integer",
    "minimum": 1,
    "maximum": MAX_REVIEW_PAGES,
    "description": f"Review pages of 50 to read (default {MAX_REVIEW_PAGES}); fewer pages is faster",
}

TOOLS: List[Dict[str, Any]] = [
    {
        "name": "inspect_app",
        "title": "Inspect an App Store app",
        "description": (
            "Check whether an iOS/macOS App Store app is still as good as its star rating says. "
            "Compares the lifetime rating with the average of the most recent written reviews, "
            "breaks it down per app version (flagging regressions) and lists complaint themes from 1-2 star reviews."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"app": _APP, "country": _COUNTRY, "days": _DAYS, "pages": _PAGES},
            "required": ["app"],
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "compare_apps",
        "title": "Compare App Store apps",
        "description": "Inspect several App Store apps and rank them by how far recent reviews trail the lifetime rating.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "apps": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 10, "description": "Ids, URLs or names"},
                "country": _COUNTRY,
                "days": _DAYS,
                "pages": _PAGES,
            },
            "required": ["apps"],
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "inspect_app_countries",
        "title": "Inspect one app across storefronts",
        "description": "Inspect the same App Store app in several countries; rating gaps and complaints often differ by storefront.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app": {"type": "string", "description": "App Store id or URL"},
                "countries": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8, "description": "Two-letter storefront codes"},
                "days": _DAYS,
                "pages": _PAGES,
            },
            "required": ["app", "countries"],
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
    {
        "name": "search_apps",
        "title": "Search the App Store",
        "description": "Find App Store apps by name and return their ids, sellers, ratings and prices. Use it to pin the right id before inspecting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "term": {"type": "string", "description": "Search text"},
                "country": _COUNTRY,
                "limit": {"type": "integer", "minimum": 1, "maximum": 25, "description": "Max results (default 8)"},
            },
            "required": ["term"],
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": True},
    },
]


class ToolError(Exception):
    """A tool failed in a way the model should see (returned as isError content)."""


def _int(args: Dict[str, Any], key: str, default: int, lo: int, hi: int) -> int:
    val = args.get(key, default)
    if isinstance(val, bool) or not isinstance(val, int):
        raise ToolError(f"'{key}' must be an integer")
    return max(lo, min(hi, val))


def _str(args: Dict[str, Any], key: str, required: bool = False) -> Optional[str]:
    val = args.get(key)
    if val is None or val == "":
        if required:
            raise ToolError(f"'{key}' is required")
        return None
    if not isinstance(val, str):
        raise ToolError(f"'{key}' must be a string")
    return val.strip()


def _str_list(args: Dict[str, Any], key: str, max_items: int) -> List[str]:
    val = args.get(key)
    if not isinstance(val, list) or not val or not all(isinstance(x, str) and x.strip() for x in val):
        raise ToolError(f"'{key}' must be a non-empty list of strings")
    if len(val) > max_items:
        raise ToolError(f"'{key}' takes at most {max_items} items")
    return [x.strip() for x in val]


def run_tool(name: str, args: Dict[str, Any], get: Callable = http_get_json) -> Dict[str, Any]:
    """Run one tool and return an MCP tool result. Raises ToolError for bad input."""
    from .cli import _report  # local import: cli imports nothing from here

    if not isinstance(args, dict):
        raise ToolError("arguments must be an object")
    try:
        if name == "inspect_app":
            report = _report(_str(args, "app", True), _str(args, "country"), _int(args, "pages", MAX_REVIEW_PAGES, 1, MAX_REVIEW_PAGES), _int(args, "days", 30, 1, 365), get)
            return {"content": [{"type": "text", "text": to_markdown(report)}], "structuredContent": report}

        if name == "compare_apps":
            refs = _str_list(args, "apps", 10)
            pages = _int(args, "pages", MAX_REVIEW_PAGES, 1, MAX_REVIEW_PAGES)
            days = _int(args, "days", 30, 1, 365)
            reports = [_report(ref, _str(args, "country"), pages, days, get) for ref in refs]
            return {"content": [{"type": "text", "text": compare_markdown(reports)}], "structuredContent": {"apps": reports}}

        if name == "inspect_app_countries":
            app = _str(args, "app", True)
            pages = _int(args, "pages", MAX_REVIEW_PAGES, 1, MAX_REVIEW_PAGES)
            days = _int(args, "days", 30, 1, 365)
            reports = []
            for cc in _str_list(args, "countries", 8):
                rep = _report(app, cc, pages, days, get)
                rep["app"] = dict(rep["app"], name=f"{rep['app'].get('name')} [{cc.lower()}]")
                reports.append(rep)
            return {"content": [{"type": "text", "text": compare_markdown(reports)}], "structuredContent": {"apps": reports}}

        if name == "search_apps":
            term = _str(args, "term", True)
            found = search(term, (_str(args, "country") or "us").lower(), _int(args, "limit", 8, 1, 25), get=get)
            rows = [
                {k: x.get(k) for k in ("trackId", "trackName", "sellerName", "averageUserRating", "userRatingCount", "formattedPrice", "trackViewUrl")}
                for x in found
            ]
            lines = [f"- {r['trackName']} (id {r['trackId']}) by {r['sellerName']}: {r['averageUserRating'] or 0:.2f}★ from {r['userRatingCount'] or 0:,} ratings, {r['formattedPrice']}" for r in rows]
            return {"content": [{"type": "text", "text": "\n".join(lines) or "No apps found."}], "structuredContent": {"results": rows}}
    except AppInspectError as exc:
        return {"content": [{"type": "text", "text": f"app-inspect: {exc}"}], "isError": True}
    raise KeyError(name)


def _result(msg_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _error(msg_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def handle(message: Any, get: Callable = http_get_json) -> Optional[Dict[str, Any]]:
    """Handle one JSON-RPC message; return the response, or None for notifications."""
    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return _error(None, -32600, "Invalid Request")
    method, msg_id = message.get("method"), message.get("id")
    params = message.get("params") or {}
    is_notification = "id" not in message

    if method == "initialize":
        asked = params.get("protocolVersion")
        version = asked if asked in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
        return _result(
            msg_id,
            {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "app-inspect", "title": "app-inspect", "version": __version__},
                "instructions": "Read-only App Store review checks. Use search_apps to pin an app id, then inspect_app or compare_apps.",
            },
        )
    if method == "ping":
        return _result(msg_id, {})
    if method == "tools/list":
        return _result(msg_id, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        if name not in {t["name"] for t in TOOLS}:
            return _error(msg_id, -32602, f"Unknown tool: {name}")
        try:
            return _result(msg_id, run_tool(name, params.get("arguments") or {}, get))
        except ToolError as exc:
            return _result(msg_id, {"content": [{"type": "text", "text": f"Invalid arguments: {exc}"}], "isError": True})
        except Exception as exc:  # network failure etc.: report to the model, keep the server alive
            return _result(msg_id, {"content": [{"type": "text", "text": f"app-inspect failed: {exc}"}], "isError": True})
    if is_notification:
        return None  # notifications/initialized, notifications/cancelled, ...
    return _error(msg_id, -32601, f"Method not found: {method}")


def serve(stdin=None, stdout=None, get: Callable = http_get_json) -> int:
    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            response: Optional[Dict[str, Any]] = _error(None, -32700, "Parse error")
        else:
            if isinstance(message, list):  # batches were removed from the spec; answer each anyway
                replies = [r for r in (handle(m, get) for m in message) if r is not None]
                response = replies or None  # type: ignore[assignment]
            else:
                response = handle(message, get)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0
