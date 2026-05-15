# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-05-15

### Added

- **Hybrid runner routing in the Telegram bot**. `URL_ROUTES` entries now accept an optional `fallback_workflow` field. When the route's repo has no online self-hosted runner, the bot dispatches `fallback_workflow` instead of the primary `workflow`. Removes the previous limitation that paired pipelines (e.g. `youtube-to-obsidian`) only ran while the user's self-hosted machine was on.
- `bot/app.py::_has_online_selfhosted_runner(repo)` — lightweight GitHub API call (`GET /repos/{owner}/{repo}/actions/runners`) that decides primary vs. fallback at dispatch time. Network failures are treated as "online unknown" so we never fall back spuriously.
- Bot replies now annotate fallback dispatches (`(self-hosted runner offline — using GHA fallback)`) so the user knows why a slower path was taken.
- 5 new tests in `tests/test_bot_url_route.py` covering: primary path with online runner, fallback path with no runners, fallback path with all-offline runners, network-error → primary, non-hybrid routes never call the runner API.

### Changed

- `URL_ROUTES` env-var schema docstring updated to list `fallback_workflow` as an optional field. Existing routes without this field continue to work identically (no API call to /runners, no fallback selection).

### Why this matters

Up through v0.5.0, the Notes_project / youtube-to-obsidian pipeline required the user's self-hosted runner to be online — typically a laptop on home Wi-Fi, since YouTube blocks the transcript scrape from cloud-provider IPs. If the laptop slept or WSL was shut down, every shared YouTube link queued indefinitely on a runner that was never coming back.

v0.6.0 makes the bot aware of runner availability and falls back to GHA-hosted runners (paired with a WebShare residential proxy at the workflow level) when the on-prem path is offline. The user's experience is now "always works", with the fast path used when available and the slower-but-always-available path used otherwise.

## [0.5.0] - 2026-05-15

### Added

- `auto_project.youtube` subpackage exposing `categories.lookup(category_id) → (en, ko)` — the canonical YouTube Data API `videoCategoryId` mapping. Consumer projects (`youtube-to-obsidian`, `Notes_project`) import from here rather than maintaining their own copy.

## [0.4.0] - 2026-05-15

### Added

- **URL routing in the Telegram bot** via the `URL_ROUTES` env var (JSON array). Any non-command message containing a URL is matched against the routes and the first hit's workflow is dispatched on its repo with the URL passed as the named input. Complements the existing explicit `/add <url>` command — `/add` is manual, `URL_ROUTES` is automatic and supports multiple targets (e.g. YouTube → summarizer, arXiv → reader).
- 8 unit tests for URL extraction, pattern matching, dispatch payload, and `/add` coexistence.

## [0.3.0] - prior

### Added

- Cloud Run Telegram bot service (`bot/`) — phone → bot → `workflow_dispatch` plumbing.
- `notify.py` — one-way Telegram alerts.

## [0.2.0] - prior

### Added

- `notify.py` initial release.

## [0.1.0] - prior

### Added

- Initial framework: `llm.py` (Gemini → Groq → Cerebras router), `state.py` (per-project JSON state), `__main__.py` runner.

[Unreleased]: https://github.com/Sweet-Butters/auto_project/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/Sweet-Butters/auto_project/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Sweet-Butters/auto_project/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Sweet-Butters/auto_project/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Sweet-Butters/auto_project/releases/tag/v0.3.0
[0.2.0]: https://github.com/Sweet-Butters/auto_project/releases/tag/v0.2.0
[0.1.0]: https://github.com/Sweet-Butters/auto_project/releases/tag/v0.1.0
