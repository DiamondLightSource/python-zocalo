from zocalo.configuration.plugins import Plugin, PluginSchema
from marshmallow import fields


class ISPyBSchema(PluginSchema):
    config = fields.Str(required=True)


class ISPyB(Plugin):
    schema = ISPyBSchema()


default = ISPyB
