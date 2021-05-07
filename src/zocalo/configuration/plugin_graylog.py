from marshmallow import fields, validate

from zocalo.configuration import PluginSchema


class Graylog(PluginSchema):
    protocol = fields.Str(validate=validate.OneOf(["UDP", "TCP"]), required=True)
    host = fields.Str(required=True)
    port = fields.Int(required=True)

    @staticmethod
    def activate(configuration):
        raise NotImplementedError("Make a thing happen!")
