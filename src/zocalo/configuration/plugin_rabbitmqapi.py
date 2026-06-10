from __future__ import annotations

from typing import Any

from marshmallow import fields

from zocalo.configuration import PluginSchema


class RabbitAPI:
    class Schema(PluginSchema):
        base_url = fields.Str(required=True)
        username = fields.Str(required=True)
        password = fields.Str(required=True)
        vhost = fields.Str()

    @staticmethod
    def activate(configuration: dict[str, Any]) -> dict[str, Any]:
        configuration.setdefault("vhost", "/")
        return configuration
