# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-11-03

### Added
- `app-inspect watch <app>`: appends a snapshot (lifetime rating, recent average, gap level, version, flagged regressions) to a JSONL history file, prints what changed since the previous snapshot and a trend table.
- `--fail-on-change` exits 4 when a rating fell, the gap level worsened or a new version regression appeared; `--min-drop`, `--no-save`, `--history`, `-f json`.
- `examples/watch-app.yml`: a scheduled GitHub Action that keeps the history in your repo.

## [0.1.0] - 2026-11-02

First working release (the repository previously held only an empty README).

### Added
- `app-inspect <id | App Store URL | name>`: lifetime rating vs. the average of up
  to 500 most recent written reviews, a last-N-days window, the current version's
  reviews, and a gap level (`in line`, `drifting`, `big gap`, `improving`).
- Per-version averages with regression flags (≥0.5★ drop vs. the previous version
  with at least 5 reviews).
- Complaint themes from 1–2★ reviews (crashes, pricing/subscription, ads, login,
  performance, data loss/sync, update regressions, privacy, support) with a quote each.
- `app-inspect compare <app> <app> ...`: rank several apps by gap.
- `app-inspect search <term>`: find app ids.
- Text, Markdown and JSON output; `--country`, `--pages`, `--days`.
- `--max-gap N` exits with code 3 when the gap exceeds N, for developers monitoring
  their own app in CI or cron.
- An Agent Skill (`skills/app-inspect/SKILL.md`) for Claude Code, Codex and other
  agents that support SKILL.md.
- Offline test suite and GitHub Actions CI on Python 3.9–3.13.

[0.1.0]: https://github.com/Harrison0223-svg/app-inspect-cli/releases/tag/v0.1.0
