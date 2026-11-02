# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

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
