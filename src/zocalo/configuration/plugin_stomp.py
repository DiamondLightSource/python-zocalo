from marshmallow import fields
from workflows.transport.stomp_transport import StompTransport

from zocalo.configuration import PluginSchema


class Stomp(PluginSchema):
    host = fields.Str(required=True)
    port = fields.Int(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    prefix = fields.Str(required=True)

    @staticmethod
    def activate(configuration):
        for cfgoption, target in [
            ("host", "--stomp-host"),
            ("port", "--stomp-port"),
            ("password", "--stomp-pass"),
            ("username", "--stomp-user"),
            ("prefix", "--stomp-prfx"),
        ]:
            StompTransport.defaults[target] = configuration[cfgoption]