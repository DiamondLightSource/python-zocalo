from zocalo.configuration.plugins import Plugin, PluginSchema
from marshmallow import fields


class JMXSchema(PluginSchema):
    host = fields.Str(required=True)
    port = fields.Int(required=True)
    base_url = fields.Str(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class JMX(Plugin):
    schema = JMXSchema()


default = JMX
