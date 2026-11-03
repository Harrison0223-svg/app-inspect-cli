---
name: app-inspect
description: Check whether an iOS / App Store app is still as good as its star rating says, before the user downloads or pays for it. Use when the user asks if an App Store app is worth it, whether its rating is trustworthy, how recent reviews look, what people complain about, or to compare several iPhone/iPad/Mac apps. Not for Google Play or for writing reviews.
---

# app-inspect

`app-inspect` reads Apple's public, keyless App Store feeds and compares an app's lifetime
rating with what recent written reviewers say, per version, with the top complaint themes.

## Setup

```sh
pipx install git+https://github.com/Harrison0223-svg/app-inspect-cli   # or: pip install --user ...
app-inspect --version
```

Python 3.9+, no dependencies, no API key.

## Use

Always ask for JSON so you can read fields instead of parsing text:

```sh
app-inspect "<app name, id, or App Store URL>" --format json          # one app
app-inspect compare <app> <app> [...] --format json                   # several
app-inspect search "<name>" --format json                             # find the right id first
```

- Pass `--country xx` (two-letter storefront) when the user is outside the US or names a store.
- When a name matches several apps, run `search` first and pin the id; the CLI prints the match it chose on stderr.

## Reading the result

- `ratings.gap` = lifetime average − recent written-review average. `gap_level`: `in line` (<1),
  `drifting` (1–2), `big gap` (≥2), `improving` (≤ −0.5).
- Written reviews skew negative for every app, so a gap of ~1 is normal. Compare apps with
  `compare` rather than treating one gap as absolute. Say this to the user when it matters.
- `versions[].regression` marks a version whose average fell ≥0.5★ below the previous version
  with enough reviews. `themes` lists what 1–2★ reviewers complain about, with one short quote.
- `ratings.sample_from/sample_to` is the window the reviews cover; busy apps cover only days.
- Report: the two averages, the gap level, the main complaint, any regression, the verdict.
  Quote reviews sparingly and never present the verdict as Apple's.

## Tracking over time
`app-inspect watch <app> --history FILE [--fail-on-change]` appends a snapshot and prints changes since the last run (exit 4 if worse). Use it for recurring monitoring.
