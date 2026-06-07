"""Tests for entity platforms (sensor, binary_sensor, calendar, todo)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from freezegun import freeze_time
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


def _slot(date_iso: str, **extra: object) -> dict[str, object]:
    """Return a meal-plan slot stub."""
    base = {
        "id": "slot",
        "date": date_iso,
        "title": "Spaghetti",
        "recipeId": "r1",
        "course": "dinner",
        "servings": 2,
    }
    base.update(extra)
    return base


async def test_meals_planned_this_week_counts_iso_week(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The meals-this-week sensor counts only slots in the current ISO week."""
    coordinator = setup_integration.runtime_data.coordinator
    with freeze_time("2099-01-13T12:00:00Z"):
        coordinator.async_set_updated_data(
            {
                "meal_plans": [
                    {
                        "id": "current",
                        "name": "Meal Plan",
                        "slots": [
                            _slot("2099-01-15T18:00:00Z", id="in-week"),
                            _slot("2099-02-15T18:00:00Z", id="next-month"),
                            _slot("not-a-date", id="bad"),
                            {"id": "no-date", "title": "x"},  # KeyError
                        ],
                    }
                ],
                "shopping_lists": [],
                "pantry_items": [],
            }
        )
        await hass.async_block_till_done()
        state = hass.states.get("sensor.culiplan_meals_planned_this_week")
        assert state is not None
        assert state.state == "1"


async def test_shopping_items_count(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The shopping-items count ignores ``completed`` items."""
    state = hass.states.get("sensor.culiplan_shopping_items")
    assert state is not None
    assert state.state == "1"


async def test_expiring_pantry_items_window(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The pantry-expiring sensor reflects the data and window."""
    coordinator = setup_integration.runtime_data.coordinator
    now = datetime.now(tz=UTC)
    coordinator.async_set_updated_data(
        {
            "meal_plans": [],
            "shopping_lists": [],
            "pantry_items": [
                {"id": "p1", "expiresAt": (now + timedelta(days=1)).isoformat()},
                {"id": "p2", "expiresAt": (now + timedelta(days=10)).isoformat()},
                {"id": "p3"},  # no expiry — skipped
                {"id": "p4", "expiresAt": "invalid"},  # bad parse — skipped
            ],
        }
    )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.culiplan_expiring_pantry_items")
    assert state is not None
    assert state.state == "1"
    assert state.attributes["expiring_item_ids"] == ["p1"]
    assert state.attributes["expiry_window_days"] == 3


async def test_pantry_has_expiring_binary(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The pantry binary sensor turns on when within the hour-window."""
    coordinator = setup_integration.runtime_data.coordinator
    now = datetime.now(tz=UTC)

    coordinator.async_set_updated_data(
        {
            "meal_plans": [],
            "shopping_lists": [],
            "pantry_items": [
                {"id": "p1", "expiresAt": (now + timedelta(hours=2)).isoformat()},
                {"id": "p2"},  # no expiry — skipped
                {"id": "p3", "expiresAt": "bad"},  # bad — skipped
            ],
        }
    )
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.culiplan_pantry_has_expiring_items")
    assert state is not None
    assert state.state == STATE_ON
    assert state.attributes["expiring_item_ids"] == ["p1"]
    assert state.attributes["expiry_window_hours"] == 48


async def test_pantry_has_expiring_off_when_empty(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The pantry binary sensor is off when no items expire soon."""
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.async_set_updated_data(
        {"meal_plans": [], "shopping_lists": [], "pantry_items": []}
    )
    await hass.async_block_till_done()
    state = hass.states.get("binary_sensor.culiplan_pantry_has_expiring_items")
    assert state is not None
    assert state.state == STATE_OFF


async def test_calendar_entity_state_and_events(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The calendar entity surfaces the upcoming event."""
    coordinator = setup_integration.runtime_data.coordinator
    # Use a far-future date so the calendar's current/next event is always
    # this one regardless of when the test runs.
    coordinator.async_set_updated_data(
        {
            "meal_plans": [
                {
                    "id": "current",
                    "name": "Meal Plan",
                    "slots": [
                        _slot("2199-01-15T18:00:00Z", id="s1"),
                        _slot("not-a-date", id="s3"),  # malformed → logged & skipped
                    ],
                }
            ],
            "shopping_lists": [],
            "pantry_items": [],
        }
    )
    await hass.async_block_till_done()
    state = hass.states.get("calendar.culiplan_meal_plan")
    assert state is not None
    assert state.attributes["recipe_id"] == "r1"


async def test_calendar_async_get_events(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """`async_get_events` returns events in the requested window."""
    coordinator = setup_integration.runtime_data.coordinator
    coordinator.async_set_updated_data(
        {
            "meal_plans": [
                {
                    "id": "current",
                    "name": "Meal Plan",
                    "slots": [_slot("2199-01-15T18:00:00Z", id="s1")],
                }
            ],
            "shopping_lists": [],
            "pantry_items": [],
        }
    )
    await hass.async_block_till_done()
    entity_id = "calendar.culiplan_meal_plan"
    res = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": entity_id,
            "start_date_time": datetime(2199, 1, 14, tzinfo=UTC),
            "end_date_time": datetime(2199, 1, 16, tzinfo=UTC),
        },
        blocking=True,
        return_response=True,
    )
    events = res[entity_id]["events"]
    assert len(events) == 1
    assert events[0]["summary"] == "Spaghetti"


async def test_todo_list_items(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """The todo entity reflects coordinator items."""
    res = await hass.services.async_call(
        "todo",
        "get_items",
        {"entity_id": "todo.culiplan_shopping_list"},
        blocking=True,
        return_response=True,
    )
    items = res["todo.culiplan_shopping_list"]["items"]
    summaries = sorted(i["summary"] for i in items)
    assert summaries == ["Bread", "Milk"]


async def test_todo_mutations(
    hass: HomeAssistant, setup_integration: MockConfigEntry
) -> None:
    """Add / update / delete invoke the API client."""
    client = setup_integration.runtime_data.client

    await hass.services.async_call(
        "todo",
        "add_item",
        {"entity_id": "todo.culiplan_shopping_list", "item": "Eggs"},
        blocking=True,
    )
    client.async_add_shopping_item.assert_awaited_with(name="Eggs")

    await hass.services.async_call(
        "todo",
        "update_item",
        {
            "entity_id": "todo.culiplan_shopping_list",
            "item": "item-1",
            "status": "completed",
        },
        blocking=True,
    )
    client.async_update_shopping_item.assert_awaited()

    await hass.services.async_call(
        "todo",
        "remove_item",
        {"entity_id": "todo.culiplan_shopping_list", "item": "item-1"},
        blocking=True,
    )
    client.async_remove_shopping_item.assert_awaited_with(item_id="item-1")
