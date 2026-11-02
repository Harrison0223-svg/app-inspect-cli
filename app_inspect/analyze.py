"""Turn an app's lookup record and recent reviews into an inspection report.

Everything here is pure: no network, so it is easy to test."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

# Complaint themes, matched case-insensitively against title + body of 1-2 star reviews.
THEMES: Dict[str, List[str]] = {
    "crashes & bugs": [r"crash", r"bug", r"glitch", r"freez", r"broken", r"not working", r"doesn'?t work", r"won'?t (?:open|load|work)", r"error"],
    "subscription & pricing": [r"subscri", r"pay ?wall", r"premium", r"\bpric(?:e|es|ey|ing)\b", r"expensive", r"\bcharg(?:ed|es|ing me)\b", r"refund", r"free trial", r"\btrial\b", r"rip ?off", r"\$\d"],
    "ads": [r"\bads?\b", r"advert", r"commercial"],
    "login & account": [r"log ?in", r"sign ?in", r"password", r"account", r"verif", r"locked out", r"2fa", r"disabled", r"suspended"],
    "performance & battery": [r"slow", r"lag", r"battery", r"drain", r"loading", r"takes forever"],
    "data loss & sync": [r"lost (?:all|my)", r"data loss", r"deleted", r"sync", r"backup", r"disappear"],
    "update regressions": [r"(?:new|latest|recent) (?:update|version)", r"since (?:the )?update", r"after (?:the )?update", r"bring back", r"old version"],
    "privacy & tracking": [r"privacy", r"tracking", r"permissions?\b", r"\bspy", r"personal data", r"sell(?:s|ing)? (?:my|your) data"],
    "support": [r"customer service", r"support", r"no response", r"never (?:replied|responded)", r"contact(?:ed)? (?:them|support|you)"],
}
_THEME_RX = {name: re.compile("|".join(pats), re.I) for name, pats in THEMES.items()}


def parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def version_key(v: Optional[str]) -> Tuple:
    parts = re.findall(r"\d+", v or "")
    return tuple(int(p) for p in parts) if parts else (-1,)


def mean(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 2) if xs else None


def distribution(ratings: List[int]) -> Dict[str, int]:
    c = Counter(ratings)
    return {str(s): c.get(s, 0) for s in range(5, 0, -1)}


def per_version(reviews: List[Dict[str, Any]], min_n: int = 5, drop: float = 0.5) -> List[Dict[str, Any]]:
    groups: Dict[str, List[int]] = defaultdict(list)
    for r in reviews:
        if r.get("version"):
            groups[r["version"]].append(r["rating"])
    rows = []
    prev_ok: Optional[Dict[str, Any]] = None
    for v in sorted(groups, key=version_key):
        xs = groups[v]
        row = {"version": v, "reviews": len(xs), "average": mean(xs), "low_sample": len(xs) < min_n, "regression": False}
        if not row["low_sample"]:
            if prev_ok and row["average"] is not None and prev_ok["average"] - row["average"] >= drop:
                row["regression"] = True
                row["vs_version"] = prev_ok["version"]
            prev_ok = row
        rows.append(row)
    return rows


def themes(reviews: List[Dict[str, Any]], max_rating: int = 2, samples: int = 1, snippet: int = 160) -> List[Dict[str, Any]]:
    low = [r for r in reviews if r["rating"] <= max_rating]
    out = []
    for name, rx in _THEME_RX.items():
        hits = [r for r in low if rx.search(f"{r.get('title','')} {r.get('content','')}")]
        if not hits:
            continue
        hits.sort(key=lambda r: (r.get("votes", 0), r.get("updated") or ""), reverse=True)
        quotes = []
        for r in hits[:samples]:
            text = " ".join(f"{r.get('title','')}. {r.get('content','')}".split())
            quotes.append(text if len(text) <= snippet else text[: snippet - 1].rstrip() + "…")
        out.append({"theme": name, "reviews": len(hits), "share_of_low": round(len(hits) / len(low), 2), "quotes": quotes})
    out.sort(key=lambda t: -t["reviews"])
    return out


def gap_level(gap: Optional[float]) -> str:
    if gap is None:
        return "unknown"
    if gap >= 2.0:
        return "big gap"
    if gap >= 1.0:
        return "drifting"
    if gap <= -0.5:
        return "improving"
    return "in line"


def inspect(app: Dict[str, Any], reviews: List[Dict[str, Any]], now: Optional[datetime] = None, recent_days: int = 30) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    lifetime = app.get("averageUserRating")
    lifetime = round(float(lifetime), 2) if lifetime is not None else None
    ratings = [r["rating"] for r in reviews]
    recent_avg = mean(ratings)
    dates = [d for d in (parse_time(r.get("updated")) for r in reviews) if d]

    cutoff = now - timedelta(days=recent_days)
    window = [r["rating"] for r in reviews if (parse_time(r.get("updated")) or now) >= cutoff]

    cur_v = app.get("version")
    cur = [r["rating"] for r in reviews if cur_v and r.get("version") == cur_v]

    released = parse_time(app.get("currentVersionReleaseDate"))
    days_since_update = (now - released).days if released else None

    gap = round(lifetime - recent_avg, 2) if (lifetime is not None and recent_avg is not None) else None
    versions = per_version(reviews)
    regressions = [v for v in versions if v["regression"]]
    flags: List[str] = []
    level = gap_level(gap)
    if level in ("big gap", "drifting"):
        flags.append(f"Recent written reviews average {recent_avg}★ vs {lifetime}★ lifetime ({level}, -{gap}).")
    if cur and len(cur) >= 5 and recent_avg is not None and mean(cur) is not None and recent_avg - mean(cur) >= 0.5:
        flags.append(f"Current version {cur_v} reviews average {mean(cur)}★, below the recent sample.")
    for v in regressions:
        flags.append(f"Version {v['version']} dropped to {v['average']}★ from {v.get('vs_version')}.")
    if days_since_update is not None and days_since_update > 365:
        flags.append(f"No update in {days_since_update} days.")
    if len(reviews) < 20:
        flags.append(f"Only {len(reviews)} recent written reviews; treat the comparison as weak.")
    low_share = round(sum(1 for x in ratings if x <= 2) / len(ratings), 2) if ratings else None

    theme_rows = themes(reviews)
    report = {
        "app": {
            "id": app.get("trackId"),
            "name": app.get("trackName"),
            "seller": app.get("sellerName"),
            "genre": app.get("primaryGenreName"),
            "price": app.get("formattedPrice"),
            "version": cur_v,
            "current_version_released": app.get("currentVersionReleaseDate"),
            "days_since_update": days_since_update,
            "url": app.get("trackViewUrl"),
        },
        "ratings": {
            "lifetime_average": lifetime,
            "lifetime_count": app.get("userRatingCount"),
            "recent_written_average": recent_avg,
            "recent_written_count": len(reviews),
            "last_n_days": recent_days,
            "last_n_days_average": mean(window),
            "last_n_days_count": len(window),
            "current_version_written_average": mean(cur),
            "current_version_written_count": len(cur),
            "gap": gap,
            "gap_level": level,
            "low_star_share": low_share,
            "distribution": distribution(ratings),
            "sample_from": min(dates).isoformat() if dates else None,
            "sample_to": max(dates).isoformat() if dates else None,
        },
        "versions": versions,
        "themes": theme_rows,
        "flags": flags,
        "verdict": verdict(level, regressions, theme_rows, days_since_update, len(reviews)),
        "caveat": (
            "Apple's lifetime number includes star-only ratings; the review feed holds only written reviews, "
            "which skew negative everywhere. Read the gap against other apps, not as an absolute score."
        ),
    }
    return report


def verdict(level: str, regressions: List[Dict[str, Any]], theme_rows: List[Dict[str, Any]], days_since_update: Optional[int], n: int) -> str:
    if n == 0:
        return "No recent written reviews to compare against; the lifetime rating is all there is."
    top = theme_rows[0]["theme"] if theme_rows else None
    if level == "big gap":
        msg = "Recent reviewers are far less happy than the headline rating suggests"
    elif level == "drifting":
        msg = "Recent reviews run noticeably below the headline rating"
    elif level == "improving":
        msg = "Recent reviews are better than the lifetime rating"
    else:
        msg = "Recent reviews broadly match the headline rating"
    if regressions:
        msg += f"; version {regressions[-1]['version']} looks like a regression"
    if top and level in ("big gap", "drifting"):
        msg += f"; the main complaint is {top}"
    if days_since_update is not None and days_since_update > 365:
        msg += "; and it hasn't been updated in over a year"
    return msg + "."
