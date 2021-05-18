"""Top-level package for Zocalo."""

import logging
import socket
import warnings

import graypy
import graypy.handler

__author__ = "Markus Gerstel"
__email__ = "scientificsoftware@diamond.ac.uk"
__version__ = "0.8.0"

logging.getLogger("zocalo").addHandler(logging.NullHandler())


class ConfigurationError(Exception):
    pass


def enable_graylog(host="graylog2.diamond.ac.uk", port=12201, cache_dns=True):
    """
    Enable logging to a Graylog server. By default this is set up to log to
    the default index at the Diamond Light Source central graylog instance.
    :param host: Graylog server hostname (optional)
    :param port: Graylog server UDP port (optional)
    :param cache_dns: Look up the hostname only once on set up (default: True)
    :return: graypy log handler
    """

    warnings.warn(
        "zocalo.enable_graylog has deprecated and will be removed in a future version. "
        "You should use a zocalo configuration file instead",
        DeprecationWarning,
        stacklevel=2,
    )

    # Monkeypatch graypy to support graylog log levels:
    # Translate Python integer level numbers to syslog levels
    class PythonLevelToSyslogConverter:
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

    graypy.handler.SYSLOG_LEVELS = PythonLevelToSyslogConverter()

    # Create and enable graylog handler
    try:
        handler = graypy.GELFUDPHandler
    except AttributeError:
        handler = graypy.GELFHandler  # graypy < 1.0
    if cache_dns:
        try:
            host = socket.gethostbyname(host)
        except Exception:
            pass
    graylog = handler(host, port, level_names=True)
    logger = logging.getLogger()
    logger.addHandler(graylog)

    # Return the handler, which may be useful to attach filters to it.
    return graylog
