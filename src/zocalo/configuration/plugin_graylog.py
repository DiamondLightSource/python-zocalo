import logging
import socket

import graypy.handler
from marshmallow import fields, validate

from zocalo.configuration import PluginSchema


class _PythonLevelToSyslogConverter:
    """
    A helper class to monkeypatch graypy to support log levels in graylog.
    This translates Python integer level numbers to syslog levels.
    """

    @staticmethod
    def get(level, _):
        if level < 20:
            return 7  # DEBUG
        elif level < 25:
            return 6  # INFO
        elif level < 30:
            return 5  # NOTICE
        elif level < 40:
            return 4  # WARNING
        elif level < 50:
            return 3  # ERROR
        elif level < 60:
            return 2  # CRITICAL
        else:
            return 1  # ALERT


class Graylog:
    """
    A plugin to enable logging to a Graylog server using graypy.
    """

    class Schema(PluginSchema):
        protocol = fields.Str(validate=validate.OneOf(["UDP", "TCP"]), required=True)
        host = fields.Str(required=True)
        port = fields.Int(required=True)

    @staticmethod
    def activate(configuration):
        graypy.handler.SYSLOG_LEVELS = _PythonLevelToSyslogConverter()

        # Create and enable graylog handler
        if configuration["protocol"] == "UDP":
            handler = graypy.GELFUDPHandler
        else:
            handler = graypy.GELFTCPHandler
        host = configuration["host"]
        try:
            # Attempt to look up the hostname only once during setup
            host = socket.gethostbyname(host)
        except Exception:
            pass
        graylog = handler(host, configuration["port"], level_names=True)
        logger = logging.getLogger()
        logger.addHandler(graylog)

        # Return the handler, which may be useful to attach filters to it.
        return graylog
