# app-inspect

[![CI](https://github.com/Harrison0223-svg/app-inspect-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Harrison0223-svg/app-inspect-cli/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**Is that 4.7★ app still a 4.7★ app?** `app-inspect` compares an App Store app's lifetime
rating with what recent reviewers actually say: per version, with the top complaints, in one
command. It uses Apple's public feeds only: no API key, no account, no backend, no dependencies.

[中文说明](README.zh-CN.md)

## Why

Apple's headline rating is a lifetime average that barely moves once an app has hundreds of
thousands of ratings. A bad update, a new paywall or a login bug can sink recent reviews while the
number next to **Get** stays at 4.7. A 2026 study of 120 popular apps found
[27 sitting two stars or more below their displayed rating](https://github.com/Rajeshzheng/rating-gap-study)
across recent reviews. Finding that out by hand means scrolling the "Most Recent" list on a phone.

## Install

```sh
pipx install git+https://github.com/Harrison0223-svg/app-inspect-cli
# or
pip install --user git+https://github.com/Harrison0223-svg/app-inspect-cli
```

Python 3.9 or newer. Standard library only.

## Use

```sh
app-inspect "microsoft authenticator"            # name, id, or App Store URL
app-inspect 983156458 --country gb               # another storefront
app-inspect compare 983156458 388497605 494168017
app-inspect search "notes"                       # find ids
app-inspect 983156458 --format json              # for scripts and agents
app-inspect 983156458 --format markdown          # paste into an issue or doc
```

## Example output

Run on 2 November 2026 (US store). Numbers change daily.

```text
$ app-inspect compare 983156458 388497605 494168017
app                          lifetime  recent    gap  level      top complaint
------------------------------------------------------------------------------
Microsoft Authenticator         4.71★   1.67★  +3.04  big gap    login & account
Twilio Authy                    4.67★   1.74★  +2.93  big gap    login & account
Google Authenticator            4.85★   3.61★  +1.24  drifting   login & account
```

```text
$ app-inspect 983156458
Microsoft Authenticator — Microsoft Corporation
  Productivity · Free · v6.8.57 · updated 12d ago

  Lifetime rating        4.71★  (719,913 ratings)
  Recent written reviews 1.67★  (500 reviews)
  Last 30 days           1.85★  (114 reviews)
  This version           2.06★  (54 reviews)
  Gap                    +3.04  → big gap

  5★ ███····················· 59
  4★ ························ 9
  3★ █······················· 24
  2★ █······················· 25
  1★ ██████████████████······ 383

  By version (newest last)
    6.8.52         1.52★  n=119
    ...
    6.8.57         2.06★  n=54

  What 1–2★ reviewers complain about
    login & account          209  (51% of low reviews)
      “Never works for me. Locked me out of all of my accounts because it never worked, …”
    crashes & bugs            36  (9% of low reviews)
    data loss & sync          19  (5% of low reviews)
    ...

  Flags
    ! Recent written reviews average 1.67★ vs 4.71★ lifetime (big gap, -3.04).

  Verdict: Recent reviewers are far less happy than the headline rating suggests; the main complaint is login & account.
```

Full outputs: [`docs/example-microsoft-authenticator.txt`](docs/example-microsoft-authenticator.txt),
[`docs/example-compare.txt`](docs/example-compare.txt).

## What it measures

| Field | Meaning |
|---|---|
| Lifetime rating | Apple's `averageUserRating` and count, star-only ratings included |
| Recent written reviews | Average of up to 500 most recent written reviews (Apple's feed limit) |
| Last N days / This version | The same, restricted to the window (`--days`, default 30) or the current version |
| Gap | Lifetime − recent. `in line` < 1, `drifting` 1–2, `big gap` ≥ 2, `improving` ≤ −0.5 |
| By version | Average per app version; `▼ regression` when a version with ≥5 reviews falls ≥0.5★ below the previous one |
| Complaint themes | Keyword themes in 1–2★ reviews with one quote each |

**Read the gap comparatively.** Written reviews skew negative for every app, because people who
write are more often unhappy, so a gap around 1 is normal. A gap of 3 when similar apps sit at 1 is
the signal. That is what `compare` is for. On very busy apps, 500 reviews may cover only a few days;
the report prints the date range it covers.

## For developers: watch your own app

`--max-gap` makes the command exit with code `3` when the gap passes a threshold, so a nightly
cron or CI job can alert you when recent reviews fall away from your headline rating:

```sh
app-inspect 1234567890 --max-gap 1.5 --format markdown > review-report.md || echo "rating gap alert"
```

## Use it from Claude Code, Codex or other agents

[`skills/app-inspect/SKILL.md`](skills/app-inspect/SKILL.md) is an Agent Skill. Copy the
`skills/app-inspect` folder into `~/.claude/skills/` (Claude Code) or `~/.codex/skills/` (Codex),
install the CLI, and ask things like *"Is Authy still worth installing?"* or *"Compare the top three
habit trackers by recent reviews."* The agent calls `app-inspect --format json` and reads the fields.

## Data sources

- iTunes Search and Lookup API: `https://itunes.apple.com/search`, `https://itunes.apple.com/lookup`
- Customer reviews RSS: `https://itunes.apple.com/{country}/rss/customerreviews/page={n}/id={id}/sortby=mostrecent/json`

Both are public and unauthenticated. Be polite: one inspection makes at most 11 requests.

## Development

```sh
python -m unittest discover -s tests -v   # offline; Apple is faked
python -m app_inspect 284882215           # live run from a checkout
```

Issues and pull requests are welcome. Ideas on the roadmap: Google Play support, a trend history
file for `--max-gap` monitoring, and smarter theme detection.

## License

[MIT](LICENSE)

## Watch an app over time (v0.2)

```
app-inspect watch 284882215 --history data/history.jsonl --fail-on-change
```

Each run appends a snapshot and tells you what moved since the last one (new version, rating fell, gap level changed, new regression). Exit code 4 with `--fail-on-change` when things got worse, so cron or CI can alert you. See `examples/watch-app.yml` for a weekly GitHub Action.
