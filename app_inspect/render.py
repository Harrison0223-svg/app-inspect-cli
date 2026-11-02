"""Render an inspection report as text, Markdown or JSON."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def _stars(avg: Any) -> str:
    return "–" if avg is None else f"{avg:.2f}★"


def _bar(n: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return ""
    filled = round(width * n / total)
    return "█" * filled + "·" * (width - filled)


def _count(n: Any) -> str:
    return "–" if n is None else f"{int(n):,}"


def to_json(report: Dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)


def to_text(report: Dict[str, Any], max_versions: int = 6) -> str:
    a, r = report["app"], report["ratings"]
    lines: List[str] = []
    title = f"{a['name']} — {a['seller']}" if a.get("seller") else str(a["name"])
    lines.append(title)
    meta = [x for x in (a.get("genre"), a.get("price"), f"v{a['version']}" if a.get("version") else None) if x]
    if a.get("days_since_update") is not None:
        meta.append(f"updated {a['days_since_update']}d ago")
    lines.append("  " + " · ".join(meta))
    lines.append("")
    total = r["recent_written_count"]
    lines.append(f"  Lifetime rating        {_stars(r['lifetime_average'])}  ({_count(r['lifetime_count'])} ratings)")
    lines.append(f"  Recent written reviews {_stars(r['recent_written_average'])}  ({r['recent_written_count']} reviews)")
    if r.get("last_n_days_count") and r["last_n_days_count"] != total:
        lines.append(f"  Last {r['last_n_days']} days           {_stars(r['last_n_days_average'])}  ({r['last_n_days_count']} reviews)")
    if r.get("current_version_written_count") and r["current_version_written_count"] != total:
        lines.append(f"  This version           {_stars(r['current_version_written_average'])}  ({r['current_version_written_count']} reviews)")
    if r.get("gap") is not None:
        lines.append(f"  Gap                    {r['gap']:+.2f}  → {r['gap_level']}")
    lines.append("")
    for star, n in r["distribution"].items():
        lines.append(f"  {star}★ {_bar(n, total)} {n}")
    if report["versions"]:
        lines.append("")
        lines.append("  By version (newest last)")
        for v in report["versions"][-max_versions:]:
            mark = "  ▼ regression" if v["regression"] else ("  (few reviews)" if v["low_sample"] else "")
            lines.append(f"    {v['version']:<14} {_stars(v['average'])}  n={v['reviews']}{mark}")
    if report["themes"]:
        lines.append("")
        lines.append("  What 1–2★ reviewers complain about")
        for t in report["themes"][:5]:
            lines.append(f"    {t['theme']:<24} {t['reviews']:>3}  ({int(t['share_of_low'] * 100)}% of low reviews)")
            for q in t["quotes"]:
                lines.append(f"      “{q}”")
    if report["flags"]:
        lines.append("")
        lines.append("  Flags")
        for f in report["flags"]:
            lines.append(f"    ! {f}")
    lines.append("")
    lines.append(f"  Verdict: {report['verdict']}")
    if r.get("sample_from") and r.get("sample_to"):
        lines.append(f"  Sample: {r['sample_from'][:10]} → {r['sample_to'][:10]}. {report['caveat']}")
    return "\n".join(lines)


def to_markdown(report: Dict[str, Any]) -> str:
    a, r = report["app"], report["ratings"]
    out = [f"## {a['name']}" + (f" — {a['seller']}" if a.get("seller") else ""), ""]
    if a.get("url"):
        out.append(f"[App Store page]({a['url']}) · {a.get('genre') or ''} · {a.get('price') or ''} · v{a.get('version')}")
        out.append("")
    out += [
        "| Measure | Average | Count |",
        "|---|---|---|",
        f"| Lifetime rating | {_stars(r['lifetime_average'])} | {_count(r['lifetime_count'])} |",
        f"| Recent written reviews | {_stars(r['recent_written_average'])} | {r['recent_written_count']} |",
        f"| Last {r['last_n_days']} days | {_stars(r['last_n_days_average'])} | {r['last_n_days_count']} |",
        f"| This version | {_stars(r['current_version_written_average'])} | {r['current_version_written_count']} |",
        "",
    ]
    if r.get("gap") is not None:
        out += [f"**Gap:** {r['gap']:+.2f} ({r['gap_level']})", ""]
    if report["themes"]:
        out += ["| Complaint theme (1–2★) | Reviews | Share |", "|---|---|---|"]
        for t in report["themes"][:6]:
            out.append(f"| {t['theme']} | {t['reviews']} | {int(t['share_of_low'] * 100)}% |")
        out.append("")
    if report["flags"]:
        out += [f"- ⚠️ {f}" for f in report["flags"]] + [""]
    out += [f"**Verdict:** {report['verdict']}", "", f"_{report['caveat']}_"]
    return "\n".join(out)


def search_table(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "No matches."
    rows = []
    for x in results:
        rows.append(
            f"{x.get('trackId'):>12}  {_stars(x.get('averageUserRating')):>6}  {_count(x.get('userRatingCount')):>11}  "
            f"{(x.get('formattedPrice') or ''):<6}  {x.get('trackName')} — {x.get('sellerName')}"
        )
    return "\n".join(["          id  rating      ratings  price   app"] + rows)


def compare_table(reports: List[Dict[str, Any]]) -> str:
    head = f"{'app':<28} {'lifetime':>8} {'recent':>7} {'gap':>6}  {'level':<10} top complaint"
    rows = [head, "-" * len(head)]
    for rep in sorted(reports, key=lambda x: -(x["ratings"]["gap"] or -99)):
        a, r = rep["app"], rep["ratings"]
        name = (a.get("name") or "?")[:28]
        gap = "–" if r["gap"] is None else f"{r['gap']:+.2f}"
        top = rep["themes"][0]["theme"] if rep["themes"] else "–"
        rows.append(f"{name:<28} {_stars(r['lifetime_average']):>8} {_stars(r['recent_written_average']):>7} {gap:>6}  {r['gap_level']:<10} {top}")
    return "\n".join(rows)


def compare_markdown(reports: List[Dict[str, Any]]) -> str:
    rows = ["| App | Lifetime | Recent written | Gap | Level | Top complaint |", "|---|---|---|---|---|---|"]
    for rep in sorted(reports, key=lambda x: -(x["ratings"]["gap"] or -99)):
        a, r = rep["app"], rep["ratings"]
        gap = "–" if r["gap"] is None else f"{r['gap']:+.2f}"
        top = rep["themes"][0]["theme"] if rep["themes"] else "–"
        name = f"[{a.get('name')}]({a['url']})" if a.get("url") else str(a.get("name"))
        rows.append(f"| {name} | {_stars(r['lifetime_average'])} | {_stars(r['recent_written_average'])} ({r['recent_written_count']}) | {gap} | {r['gap_level']} | {top} |")
    return "\n".join(rows)
