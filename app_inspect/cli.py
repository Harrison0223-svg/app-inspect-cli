"""Command line entry point.

    app-inspect <app id | App Store URL | name> [options]
    app-inspect search <term> [--country us]
    app-inspect compare <app> <app> [...] [options]
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import __version__
from .analyze import inspect
from .fetch import AppInspectError, MAX_REVIEW_PAGES, http_get_json, lookup, parse_app_ref, reviews, search
from . import watch as watchmod
from .render import compare_markdown, compare_table, search_table, to_json, to_markdown, to_text

EXIT_GAP = 3
EXIT_CHANGE = 4


def _inspect_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="app-inspect",
        description="Pre-purchase inspection for App Store apps: lifetime rating vs. what recent reviewers say.",
        epilog="Also: `app-inspect search <term>` lists matching apps; `app-inspect compare <app> <app> ...` ranks several side by side.",
    )
    p.add_argument("app", help="App Store id (284882215), App Store URL, or an app name to search for")
    p.add_argument("-c", "--country", default=None, help="two-letter storefront code (default: from URL, else us)")
    p.add_argument("-p", "--pages", type=int, default=MAX_REVIEW_PAGES, help=f"review pages of 50 to read, 1-{MAX_REVIEW_PAGES} (default {MAX_REVIEW_PAGES})")
    p.add_argument("-f", "--format", choices=("text", "json", "markdown"), default="text")
    p.add_argument("--days", type=int, default=30, help="size of the 'last N days' window (default 30)")
    p.add_argument("--max-gap", type=float, default=None, help=f"exit {EXIT_GAP} if lifetime minus recent average exceeds this (for CI/monitoring)")
    p.add_argument("-V", "--version", action="version", version=f"app-inspect {__version__}")
    return p


def _search_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app-inspect search", description="Find App Store apps by name.")
    p.add_argument("term", nargs="+")
    p.add_argument("-c", "--country", default="us")
    p.add_argument("-n", "--limit", type=int, default=8)
    p.add_argument("-f", "--format", choices=("text", "json"), default="text")
    return p


def _compare_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app-inspect compare", description="Inspect several apps and rank them by rating gap.")
    p.add_argument("apps", nargs="+", help="ids, App Store URLs or names")
    p.add_argument("-c", "--country", default=None)
    p.add_argument("-p", "--pages", type=int, default=MAX_REVIEW_PAGES)
    p.add_argument("-f", "--format", choices=("text", "json", "markdown"), default="text")
    p.add_argument("--days", type=int, default=30)
    return p


def _countries_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app-inspect countries", description="Inspect one app across several storefronts (rating gaps often differ by country).")
    p.add_argument("app", help="App Store id or URL")
    p.add_argument("countries", nargs="+", help="two-letter storefront codes, e.g. us gb de jp")
    p.add_argument("-p", "--pages", type=int, default=MAX_REVIEW_PAGES)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("-f", "--format", choices=("text", "json", "markdown"), default="text")
    return p


def _watch_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app-inspect watch", description="Record a snapshot of an app and report what changed since the last one (run it from cron or a scheduled GitHub Action).")
    p.add_argument("app")
    p.add_argument("-c", "--country", default=None)
    p.add_argument("-p", "--pages", type=int, default=MAX_REVIEW_PAGES)
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--history", default="app-inspect-history.jsonl", help="JSONL file to append to (default ./app-inspect-history.jsonl)")
    p.add_argument("--min-drop", type=float, default=0.1, help="rating change that counts as news (default 0.1)")
    p.add_argument("--no-save", action="store_true", help="compare only; do not append a snapshot")
    p.add_argument("--fail-on-change", action="store_true", help=f"exit {EXIT_CHANGE} when something got worse (rating fell, gap level worsened, new regression)")
    p.add_argument("-f", "--format", choices=("text", "json"), default="text")
    return p


def _resolve(ref: str, country_opt: Optional[str], get) -> tuple:
    app_id, url_country = parse_app_ref(ref)
    country = (country_opt or url_country or "us").lower()
    if app_id is None:
        found = search(ref, country, 1, get=get)
        if not found:
            raise AppInspectError(f"No app found for '{ref}' in the '{country}' store. Try `app-inspect search`.")
        app_id = str(found[0]["trackId"])
        print(f"Matched '{ref}' → {found[0].get('trackName')} (id {app_id}). Pass the id to pin it.", file=sys.stderr)
    return app_id, country


def _report(ref: str, country_opt: Optional[str], pages: int, days: int, get) -> dict:
    app_id, country = _resolve(ref, country_opt, get)
    report = inspect(lookup(app_id, country, get=get), reviews(app_id, country, pages, get=get), recent_days=days)
    report["country"] = country
    return report


def main(argv: Optional[List[str]] = None, get=http_get_json, out=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    out = out or sys.stdout
    try:
        if argv and argv[0] == "search":
            a = _search_parser().parse_args(argv[1:])
            res = search(" ".join(a.term), a.country, a.limit, get=get)
            if a.format == "json":
                import json

                print(json.dumps([{k: x.get(k) for k in ("trackId", "trackName", "sellerName", "averageUserRating", "userRatingCount", "formattedPrice", "trackViewUrl")} for x in res], indent=2, ensure_ascii=False), file=out)
            else:
                print(search_table(res), file=out)
            return 0

        if argv and argv[0] == "compare":
            a = _compare_parser().parse_args(argv[1:])
            reports = [_report(ref, a.country, a.pages, a.days, get) for ref in a.apps]
            if a.format == "json":
                import json

                print(json.dumps(reports, indent=2, ensure_ascii=False), file=out)
            elif a.format == "markdown":
                print(compare_markdown(reports), file=out)
            else:
                print(compare_table(reports), file=out)
            return 0

        if argv and argv[0] == "countries":
            a = _countries_parser().parse_args(argv[1:])
            reports = []
            for cc in a.countries:
                rep = _report(a.app, cc, a.pages, a.days, get)
                rep["app"] = dict(rep["app"], name=f"{rep['app'].get('name')} [{cc.lower()}]")
                reports.append(rep)
            if a.format == "json":
                import json

                print(json.dumps(reports, indent=2, ensure_ascii=False), file=out)
            elif a.format == "markdown":
                print(compare_markdown(reports), file=out)
            else:
                print(compare_table(reports), file=out)
            return 0

        if argv and argv[0] == "watch":
            a = _watch_parser().parse_args(argv[1:])
            report = _report(a.app, a.country, a.pages, a.days, get)
            snap = watchmod.snapshot(report)
            hist = watchmod.history_for(watchmod.load(a.history), snap)
            prev = hist[-1] if hist else None
            notes = watchmod.changes(prev, snap, a.min_drop)
            if not a.no_save:
                watchmod.append(a.history, snap)
            if a.format == "json":
                import json

                print(json.dumps({"snapshot": snap, "previous": prev, "changes": notes}, indent=2, ensure_ascii=False), file=out)
            else:
                print(f"{snap['name']} (id {snap['app_id']}, {snap['country']}) - {len(hist) + (0 if a.no_save else 1)} snapshot(s)", file=out)
                for n in notes:
                    print(f"  - {n}", file=out)
                print("", file=out)
                print(watchmod.trend_text(hist + ([] if a.no_save else [snap])), file=out)
            if a.fail_on_change and watchmod.worsened(prev, snap, a.min_drop):
                return EXIT_CHANGE
            return 0

        if argv and argv[0] == "inspect":
            argv = argv[1:]
        a = _inspect_parser().parse_args(argv)
        report = _report(a.app, a.country, a.pages, a.days, get)
        if a.format == "json":
            print(to_json(report), file=out)
        elif a.format == "markdown":
            print(to_markdown(report), file=out)
        else:
            print(to_text(report), file=out)
        gap = report["ratings"]["gap"]
        if a.max_gap is not None and gap is not None and gap > a.max_gap:
            return EXIT_GAP
        return 0
    except AppInspectError as exc:
        print(f"app-inspect: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
