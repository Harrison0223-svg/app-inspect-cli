"""Snapshot history: `app-inspect watch` appends one line per run to a JSONL file and reports changes."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def snapshot(report: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    r = report["ratings"]
    return {
        "time": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "app_id": report["app"]["id"],
        "name": report["app"]["name"],
        "country": report.get("country"),
        "version": report["app"]["version"],
        "lifetime_average": r["lifetime_average"],
        "lifetime_count": r["lifetime_count"],
        "recent_written_average": r["recent_written_average"],
        "last_n_days_average": r["last_n_days_average"],
        "last_n_days_count": r["last_n_days_count"],
        "gap": r["gap"],
        "gap_level": r["gap_level"],
        "regressions": [v["version"] for v in report["versions"] if v["regression"]],
    }


def load(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue  # tolerate a torn line
    return rows


def append(path: str, snap: Dict[str, Any]) -> None:
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(snap, ensure_ascii=False) + "\n")


def history_for(rows: List[Dict[str, Any]], snap: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [r for r in rows if r.get("app_id") == snap["app_id"] and r.get("country") == snap["country"]]


def changes(prev: Optional[Dict[str, Any]], cur: Dict[str, Any], min_drop: float = 0.1) -> List[str]:
    """Human-readable differences between the previous snapshot and this one."""
    if prev is None:
        return ["First snapshot recorded; changes will show from the next run."]
    out: List[str] = []
    if prev.get("version") != cur.get("version"):
        out.append(f"New version: {prev.get('version')} -> {cur.get('version')}.")
    for key, label in (("lifetime_average", "Lifetime rating"), ("last_n_days_average", "Recent-window rating"), ("recent_written_average", "Recent written average")):
        a, b = prev.get(key), cur.get(key)
        if a is not None and b is not None and abs(b - a) >= min_drop:
            out.append(f"{label} {'fell' if b < a else 'rose'}: {a} -> {b}.")
    if prev.get("gap_level") != cur.get("gap_level"):
        out.append(f"Gap level changed: {prev.get('gap_level')} -> {cur.get('gap_level')}.")
    new_reg = [v for v in cur.get("regressions", []) if v not in prev.get("regressions", [])]
    for v in new_reg:
        out.append(f"New version regression flagged: {v}.")
    return out or ["No meaningful change since the last snapshot."]


def trend_text(rows: List[Dict[str, Any]], limit: int = 10) -> str:
    rows = rows[-limit:]
    lines = [f"{'when (UTC)':<20} {'version':<10} {'lifetime':>8} {'recent':>7} {'gap':>6}  level"]
    for r in rows:
        f = lambda x: "-" if x is None else f"{x:.2f}"  # noqa: E731
        lines.append(f"{r['time']:<20} {str(r.get('version') or '-'):<10} {f(r.get('lifetime_average')):>8} {f(r.get('recent_written_average')):>7} {f(r.get('gap')):>6}  {r.get('gap_level')}")
    return "\n".join(lines)


_LEVELS = ["improving", "in line", "drifting", "big gap"]


def worsened(prev: Optional[Dict[str, Any]], cur: Dict[str, Any], min_drop: float = 0.1) -> bool:
    if prev is None:
        return False
    for key in ("lifetime_average", "last_n_days_average", "recent_written_average"):
        a, b = prev.get(key), cur.get(key)
        if a is not None and b is not None and a - b >= min_drop:
            return True
    pl, cl = prev.get("gap_level"), cur.get("gap_level")
    if pl in _LEVELS and cl in _LEVELS and _LEVELS.index(cl) > _LEVELS.index(pl):
        return True
    return any(v not in prev.get("regressions", []) for v in cur.get("regressions", []))
