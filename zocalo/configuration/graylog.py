from zocalo.configuration.plugins import Plugin, PluginSchema
from marshmallow import fields


class GraylogSchema(PluginSchema):
    protocol = fields.Str(enum=["UPD", "TCP"], required=True)
    host = fields.Str(required=True)
    port = fields.Int(required=True)


class Graylog(Plugin):
    schema = GraylogSchema()


default = Graylog
