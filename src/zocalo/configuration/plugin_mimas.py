from marshmallow import fields

from zocalo.configuration import PluginSchema


class Mimas:
    class Schema(PluginSchema):
        implementors = fields.Str()

    @staticmethod
    def activate(configuration):
        return configuration
