from __future__ import annotations

from marshmallow import fields

from zocalo.configuration import PluginSchema


class JMX:
    class Schema(PluginSchema):
        host = fields.Str(required=True)
        port = fields.Int(required=True)
        base_url = fields.Str(required=True)
        username = fields.Str(required=True)
        password = fields.Str(required=True)

    @staticmethod
    def activate(configuration):
        return configuration
