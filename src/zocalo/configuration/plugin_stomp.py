from marshmallow import fields
from workflows.transport.stomp_transport import StompTransport

from zocalo.configuration import PluginSchema


class Stomp(PluginSchema):
    host = fields.Str(required=True)
    port = fields.Int(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True)
    prefix = fields.Str(required=True)


def transport_from_config(config):
    transport_config = config.get_plugin("stomp")

    for cfgoption, target in [
        ("host", "--stomp-host"),
        ("port", "--stomp-port"),
        ("password", "--stomp-pass"),
        ("username", "--stomp-user"),
        ("prefix", "--stomp-prfx"),
    ]:
        StompTransport.defaults[target] = transport_config.get(cfgoption)
