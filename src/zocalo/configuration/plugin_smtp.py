from __future__ import annotations

from typing import Any

from marshmallow import fields

from zocalo.configuration import PluginSchema


class SMTP:
    class Schema(PluginSchema):
        host = fields.Str(required=True)
        port = fields.Int(required=True)
        from_ = fields.Email(data_key="from")

    @staticmethod
    def activate(configuration: dict[str, Any]) -> dict[str, Any]:
        return configuration
