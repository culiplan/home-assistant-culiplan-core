"""Todo entity for the Culiplan shopping list."""

from __future__ import annotations

from typing import Any

from homeassistant.components.todo import (  # type: ignore[attr-defined]
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CuliplanConfigEntry
from .coordinator import CuliplanCoordinator
from .helpers import build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CuliplanConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Culiplan todo (shopping list) entities."""
    coordinator = entry.runtime_data.coordinator
    shopping_lists = (coordinator.data or {}).get("shopping_lists", [])
    async_add_entities(
        CuliplanShoppingList(coordinator, sl, entry) for sl in shopping_lists
    )


class CuliplanShoppingList(CoordinatorEntity[CuliplanCoordinator], TodoListEntity):
    """``todo`` entity backed by the Culiplan shopping list."""

    _attr_has_entity_name = True
    _attr_translation_key = "shopping_list"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(
        self,
        coordinator: CuliplanCoordinator,
        shopping_list: dict[str, Any],
        entry: CuliplanConfigEntry,
    ) -> None:
        """Bind to a specific shopping list id within one config entry."""
        super().__init__(coordinator)
        self._list_id: str = shopping_list["id"]
        self._attr_unique_id = f"{entry.entry_id}_todo_{self._list_id}"
        self._attr_device_info = build_device_info(entry)

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the current items in this list."""
        for sl in (self.coordinator.data or {}).get("shopping_lists", []):
            if sl["id"] == self._list_id:
                return [_to_todo_item(item) for item in sl.get("items", [])]
        return []

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Add an item."""
        await self.coordinator.client.async_add_shopping_item(name=item.summary or "")
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Check or uncheck an item."""
        await self.coordinator.client.async_update_shopping_item(
            item_id=item.uid or "",
            completed=item.status == TodoItemStatus.COMPLETED,
        )
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items."""
        for uid in uids:
            await self.coordinator.client.async_remove_shopping_item(item_id=uid)
        await self.coordinator.async_request_refresh()


def _to_todo_item(item: dict[str, Any]) -> TodoItem:
    """Convert a backend item dict into a ``TodoItem``."""
    return TodoItem(
        uid=item.get("id", ""),
        summary=item.get("name", ""),
        status=(
            TodoItemStatus.COMPLETED
            if item.get("completed")
            else TodoItemStatus.NEEDS_ACTION
        ),
    )
