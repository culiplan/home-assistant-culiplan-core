"""Binary sensor entities for the Culiplan integration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CuliplanConfigEntry
from .const import CONF_EXPIRY_HOURS, DEFAULT_EXPIRY_HOURS
from .coordinator import CuliplanCoordinator
from .helpers import build_device_info, parse_dt


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CuliplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Culiplan binary sensor entities."""
    coordinator = entry.runtime_data.coordinator
    expiry_hours: int = int(entry.options.get(CONF_EXPIRY_HOURS, DEFAULT_EXPIRY_HOURS))
    async_add_entities(
        [PantryHasExpiringBinarySensor(coordinator, entry, expiry_hours)]
    )


class PantryHasExpiringBinarySensor(
    CoordinatorEntity[CuliplanCoordinator], BinarySensorEntity
):
    """``on`` when any pantry item expires within ``expiry_hours`` hours."""

    _attr_translation_key = "pantry_has_expiring"
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: CuliplanCoordinator,
        entry: CuliplanConfigEntry,
        expiry_hours: int,
    ) -> None:
        """Initialise and bind to the shared device."""
        super().__init__(coordinator)
        self._expiry_hours = expiry_hours
        self._attr_unique_id = f"{entry.entry_id}_pantry_has_expiring"
        self._attr_device_info = build_device_info(entry)

    @property
    def is_on(self) -> bool:
        """Return whether any pantry item expires within the window."""
        return len(self._expiring_ids()) > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return ID-only attributes (no PII)."""
        return {
            "expiring_item_ids": self._expiring_ids(),
            "expiry_window_hours": self._expiry_hours,
        }

    def _expiring_ids(self) -> list[str]:
        now = datetime.now(tz=UTC)
        cutoff = now + timedelta(hours=self._expiry_hours)
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
