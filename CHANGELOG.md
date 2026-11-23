# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.5.1] - 2026-11-23

### Changed
- Add bilingual quick-start examples to the README and expand the contribution guide with offline testing and issue-selection instructions.
- No CLI behavior, output schema, workflow, or runtime dependency changes.

## [0.5.0] - 2026-11-17

### Added
- `app-inspect mcp`: a zero-dependency Model Context Protocol server over stdio. Four read-only tools (`inspect_app`, `compare_apps`, `inspect_app_countries`, `search_apps`) return a Markdown summary plus structured JSON, so Claude Code, Claude Desktop, Cursor, Codex and any MCP client can check an app's review health with no API key and no hosted service. Errors (unknown app, network down) come back as tool errors; the server keeps running.
- `action.yml`: use the repo as a GitHub Action (`uses: Harrison0223-svg/app-inspect-cli@v0.5.0`). Writes the report to the job summary and fails the job with `max-gap`. Works for one app (`app`) or a portfolio (`apps-file`).
- `examples/mcp-config.json` and `examples/gap-check.yml`.

## [0.4.0] - 2026-11-07

### Added
- `app-inspect compare --file apps.txt` (or `--file -` for stdin): check a whole portfolio from a list.
- `compare --max-gap N`: exit 3 if any app's rating gap exceeds N, for CI.

## [0.3.0] - 2026-11-06

### Added
- `app-inspect countries <app> us gb de jp`: the same app across storefronts, ranked by rating gap (text/markdown/json).

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
