from marshmallow import fields

from zocalo.configuration.plugins import Plugin, PluginSchema


class StompSchema(PluginSchema):
    host = fields.Str(required=True)
    port = fields.Int(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    prefix = fields.Str(required=True)


class Stomp(Plugin):
    schema = StompSchema()


default = Stomp
