from __future__ import annotations

from marshmallow import fields

from zocalo.configuration import PluginSchema


class SMTP:
    class Schema(PluginSchema):
        host = fields.Str(required=True)
        port = fields.Int(required=True)
        from_ = fields.Email(data_key="from")

    @staticmethod
    def activate(configuration):
        return configuration
