from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from zocalo.configuration import Configuration


class Storage:
    @staticmethod
    def activate(
        configuration: dict[str, Any], config_object: Configuration
    ) -> dict[str, Any]:
        storage = config_object.storage or {}
        storage.update(configuration)
        return storage
