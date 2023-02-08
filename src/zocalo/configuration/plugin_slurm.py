from __future__ import annotations

import os

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
        user_token = configuration.get("user_token")
        if user_token and os.path.isfile(user_token):
            with open(user_token, "r") as f:
                configuration["user_token"] = f.read().strip()
        return configuration
