"""Config flow for the Culiplan integration."""

from __future__ import annotations

import logging
from typing import Any, cast

import aiohttp
from homeassistant import config_entries
from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.helpers import aiohttp_client, config_entry_oauth2_flow
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
import voluptuous as vol

from .const import (
    BASE_URL,
    CONF_EXPIRY_DAYS,
    CONF_EXPIRY_HOURS,
    DEFAULT_EXPIRY_DAYS,
    DEFAULT_EXPIRY_HOURS,
    DOMAIN,
    OAUTH_CLIENT_ID,
)

_LOGGER = logging.getLogger(__name__)


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle the Culiplan OAuth2 + reauth + reconfigure flow."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return the logger."""
        return _LOGGER

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ensure the built-in OAuth credential exists, then start OAuth."""
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential(client_id=OAUTH_CLIENT_ID, client_secret=""),
        )
        return await super().async_step_user(user_input)

    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return CuliplanOptionsFlow()

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Create the entry on successful OAuth, enforcing one entry per account."""
        account_id = await self._fetch_account_id(data)

        if self.source == config_entries.SOURCE_RECONFIGURE:
            return await self._async_finish_reconfigure(data, account_id)

        if account_id is not None:
            await self.async_set_unique_id(account_id)
            self._abort_if_unique_id_configured()

        return self.async_create_entry(title="Culiplan", data=data)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Start the re-auth flow when the API returns 401."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm the user wants to re-authenticate."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-run the OAuth flow against the existing entry."""
        return await self.async_step_user()

    # ─── Account helpers ─────────────────────────────────────────────────────

    async def _fetch_account_id(self, data: dict[str, Any]) -> str | None:
        """Fetch the Culiplan account id used as ``unique_id``."""
        token = data.get("token") or {}
        access_token = token.get("access_token") if isinstance(token, dict) else None
        if not access_token:
            return None
        session = aiohttp_client.async_get_clientsession(self.hass)
        try:
            async with session.get(
                f"{BASE_URL}/api/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                me = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.debug("Could not fetch /api/users/me for unique_id: %s", err)
            return None
        user_id = me.get("id") if isinstance(me, dict) else None
        return str(user_id) if user_id else None

    async def _async_finish_reconfigure(
        self, data: dict[str, Any], account_id: str | None
    ) -> ConfigFlowResult:
        """Apply a reconfigure result, enforcing the same Culiplan account."""
        entry = self._get_reconfigure_entry()
        if (
            entry.unique_id is not None
            and account_id is not None
            and entry.unique_id != account_id
        ):
            return self.async_abort(reason="wrong_account")
        if account_id is not None:
            await self.async_set_unique_id(account_id)
            self._abort_if_unique_id_mismatch(reason="wrong_account")
        return self.async_update_reload_and_abort(entry, data={**entry.data, **data})


class CuliplanOptionsFlow(config_entries.OptionsFlow):
    """Options for the Culiplan integration.

    Two knobs only:

    * ``expiry_days`` — window used by ``sensor.culiplan_expiring_pantry_items``.
    * ``expiry_hours`` — window used by
      ``binary_sensor.culiplan_pantry_has_expiring``.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the single options form."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_EXPIRY_DAYS,
                    default=cast(
                        int, current.get(CONF_EXPIRY_DAYS, DEFAULT_EXPIRY_DAYS)
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=30, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_EXPIRY_HOURS,
                    default=cast(
                        int, current.get(CONF_EXPIRY_HOURS, DEFAULT_EXPIRY_HOURS)
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=720, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
