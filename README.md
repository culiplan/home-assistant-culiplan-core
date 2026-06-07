# Culiplan — Home Assistant Core integration (slim)

This repository is the **Home Assistant Core-ready** subset of the
[Culiplan](https://culiplan.com) integration. It is being prepared for
submission to [`home-assistant/core`][hacore]; until that PR is merged,
it can be installed manually as a custom component.

The full-featured integration — Lovelace cards, sidebar panel, BYOK AI
dispatchers, Mealie import wizard, Voice intents, self-updater — lives
in the separate [`home-assistant-culiplan`][hacs] repository (HACS).

| Slim (this repo, Core-target) | Rich (HACS-only)          |
| ----------------------------- | ------------------------- |
| OAuth2 PKCE setup             | OAuth2 PKCE setup         |
| `calendar`, `todo`, `sensor`, `binary_sensor`, LLM API tools | Same, plus `update`, voice intents, AI services |
| 1 PyPI dep (`python-socketio`) | 4 (OpenAI / Anthropic / google-genai / socketio) |
| No bundled frontend           | Lovelace cards + sidebar panel |
| No self-updater               | Self-updater + Mealie wizard |

## Entities

| Domain          | Entity                                | Description                                     |
| --------------- | ------------------------------------- | ----------------------------------------------- |
| `calendar`      | `calendar.culiplan_meal_plan`         | One event per planned meal slot                 |
| `todo`          | `todo.culiplan_shopping_list`         | Read / write the user's Culiplan shopping list  |
| `sensor`        | `sensor.culiplan_meals_planned_this_week` | ISO-week meal count                         |
| `sensor`        | `sensor.culiplan_shopping_items`      | Unchecked shopping-list items                   |
| `sensor`        | `sensor.culiplan_expiring_pantry_items` | Pantry items expiring within N days           |
| `binary_sensor` | `binary_sensor.culiplan_pantry_has_expiring` | On when any pantry item expires soon     |

All entities attach to one `Culiplan` device per config entry. The
integration also registers a Culiplan LLM API so the user's HA
Conversation Agent (OpenAI / Anthropic / Google / Ollama / Voice
Preview) can call Culiplan tools directly.

## OAuth setup

The Culiplan backend is a public OAuth 2.1 client (PKCE S256, no
client_secret). The integration auto-imports its public credential at
setup time, so the user only sees the consent screen.

## Installation (custom component, until Core merge)

```bash
git clone https://github.com/culiplan/home-assistant-culiplan-core ~/culiplan-core
cp -r ~/culiplan-core/custom_components/culiplan \
      <ha-config>/custom_components/
```

Restart Home Assistant, then **Settings → Devices & Services → Add
Integration → Culiplan**.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install ruff mypy pytest pytest-asyncio pytest-cov \
            pytest-homeassistant-custom-component python-socketio

ruff check custom_components tests
ruff format --check custom_components tests
mypy custom_components/culiplan
pytest --cov=custom_components/culiplan --cov-fail-under=95
```

## Licence

Apache-2.0 — see [LICENSE](LICENSE).

[hacore]: https://github.com/home-assistant/core
[hacs]: https://github.com/culiplan/home-assistant-culiplan
