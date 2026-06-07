# Changelog

All notable changes to this integration will be documented here.

The format is loosely based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — Initial Core-ready build

### Added
- Slim, HA-Core-acceptable carve-out of the existing HACS integration.
- OAuth 2.1 PKCE flow with re-auth and reconfigure (same-account
  enforced).
- Options flow with two pantry-expiry knobs.
- `calendar`, `todo`, `sensor`, `binary_sensor` platforms.
- LLM API exposing 5 Culiplan tools to any HA Conversation Agent.
- Diagnostics with token redaction.
- `quality_scale.yaml` honestly targeting Silver on day one.
- CI: hassfest validation, ruff (check + format), mypy strict, pytest
  with ≥95% coverage on Python 3.13 (matches HA Core 2026.x).

### Not included (relative to HACS distribution)
- Self-updater (Core's monorepo is the update mechanism).
- Sidebar panel & Lovelace cards (frontend ships separately).
- BYOK / Local AI provider plumbing (users go through Core's
  `openai_conversation` / `anthropic` / `google_generative_ai_conversation`
  / `ollama` integrations and call Culiplan tools via the LLM API).
- Mealie import wizard (one-time data migration; doesn't belong in the
  Core config flow).
- Voice intents (ship via `home-assistant/intents` separately).
- Energy / dinner-party / cooking-mode entities & services (kept in
  the HACS distribution for now).
