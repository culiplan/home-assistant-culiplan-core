"""Sensor entities for the Culiplan integration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CuliplanConfigEntry
from .const import CONF_EXPIRY_DAYS, DEFAULT_EXPIRY_DAYS
from .coordinator import CuliplanCoordinator
from .helpers import build_device_info, parse_dt


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CuliplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Culiplan sensor entities."""
    coordinator = entry.runtime_data.coordinator
    expiry_days: int = int(entry.options.get(CONF_EXPIRY_DAYS, DEFAULT_EXPIRY_DAYS))
    async_add_entities(
        [
            MealsPlannedThisWeekSensor(coordinator, entry),
            ShoppingItemsCountSensor(coordinator, entry),
            ExpiringPantrySensor(coordinator, entry, expiry_days),
        ]
    )


class _CuliplanSensor(CoordinatorEntity[CuliplanCoordinator], SensorEntity):
    """Base for all Culiplan sensors — shared device + name handling."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: CuliplanCoordinator, entry: CuliplanConfigEntry
    ) -> None:
        """Bind to the shared device."""
        super().__init__(coordinator)
        self._attr_device_info = build_device_info(entry)


class MealsPlannedThisWeekSensor(_CuliplanSensor):
    """Number of meals planned in the current ISO week."""

    _attr_translation_key = "meals_planned_this_week"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "meals"

    def __init__(
        self, coordinator: CuliplanCoordinator, entry: CuliplanConfigEntry
    ) -> None:
        """Set a per-entry unique id."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_meals_planned_this_week"

    @property
    def native_value(self) -> int:
        """Return the meal count for the current ISO week."""
        now = datetime.now(tz=UTC)
        week_start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        week_end = week_start + timedelta(weeks=1)
        count = 0
        for plan in (self.coordinator.data or {}).get("meal_plans", []):
            for slot in plan.get("slots", []):
                try:
                    if week_start <= parse_dt(slot["date"]) < week_end:
                        count += 1
                except (KeyError, ValueError):
                    pass
        return count


class ShoppingItemsCountSensor(_CuliplanSensor):
    """Total unchecked items across all shopping lists."""

    _attr_translation_key = "shopping_items"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "items"

    def __init__(
        self, coordinator: CuliplanCoordinator, entry: CuliplanConfigEntry
    ) -> None:
        """Set a per-entry unique id."""
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_shopping_items"

    @property
    def native_value(self) -> int:
        """Return the unchecked-item count."""
        count = 0
        for sl in (self.coordinator.data or {}).get("shopping_lists", []):
            for item in sl.get("items", []):
                if not item.get("completed", False):
                    count += 1
        return count


class ExpiringPantrySensor(_CuliplanSensor):
    """Number of pantry items expiring within ``expiry_days`` days."""

    _attr_translation_key = "expiring_pantry_items"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "items"

    def __init__(
        self,
        coordinator: CuliplanCoordinator,
        entry: CuliplanConfigEntry,
        expiry_days: int,
    ) -> None:
        """Set a per-entry unique id and remember the window."""
        super().__init__(coordinator, entry)
        self._expiry_days = expiry_days
        self._attr_unique_id = f"{entry.entry_id}_expiring_pantry"

    @property
    def native_value(self) -> int:
        """Return the number of items expiring within the window."""
        return len(self._expiring_ids())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return ID-only attributes (no PII)."""
        return {
            "expiring_item_ids": self._expiring_ids(),
            "expiry_window_days": self._expiry_days,
        }

    def _expiring_ids(self) -> list[str]:
        now = datetime.now(tz=UTC)
        cutoff = now + timedelta(days=self._expiry_days)
        ids: list[str] = []
        for item in (self.coordinator.data or {}).get("pantry_items", []):
            exp = item.get("expiresAt")
            if not exp:
                continue
            try:
                if now <= parse_dt(exp) <= cutoff:
                    ids.append(item["id"])
            except (KeyError, ValueError):
                pass
        return ids
