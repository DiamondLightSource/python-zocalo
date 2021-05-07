from marshmallow import Schema, fields, validate

from zocalo.configuration import PluginSchema as PluginSchema2
from zocalo.configuration.plugins import Plugin, PluginSchema


class GraylogSchema(PluginSchema):
    protocol = fields.Str(validate=validate.OneOf(["UDP", "TCP"]), required=True)
    host = fields.Str(required=True)
    port = fields.Int(required=True)


class Graylog(Plugin):
    schema = GraylogSchema()


default = Graylog


class GraylogPlugin(PluginSchema2):
    protocol = fields.Str(validate=validate.OneOf(["UDP", "TCP"]), required=True)
    host = fields.Str(required=True)
    port = fields.Int(required=True)

    @staticmethod
    def activate(configuration):
        raise NotImplementedError("Make a thing happen!")
