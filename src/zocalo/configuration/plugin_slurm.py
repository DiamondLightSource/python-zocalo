from __future__ import annotations

from marshmallow import fields

from zocalo.configuration import PluginSchema


class Slurm:
    class Schema(PluginSchema):
        url = fields.Str(required=True)
        user_token = fields.Str(required=False)
        user = fields.Str(required=False)
        api_version = fields.Str(required=True)

    @staticmethod
    def activate(configuration):
        return configuration
