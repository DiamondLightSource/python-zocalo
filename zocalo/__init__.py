"""Top-level package for Zocalo."""

import logging

import graypy
import graypy.handler

__author__ = "Markus Gerstel"
__email__ = "scientificsoftware@diamond.ac.uk"
__version__ = "0.7.0"

logging.getLogger("zocalo").addHandler(logging.NullHandler())


def enable_graylog(host="graylog2.diamond.ac.uk", port=12201):
    """
    Enable logging to a Graylog server. By default this is set up to log to
    the default index at the Diamond Light Source central graylog instance.
    :param host: Graylog server hostname (optional)
    :param port: Graylog server UDP port (optional)
    :return: graypy log handler
    """

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
    graylog = handler(host, port, level_names=True)
    logger = logging.getLogger()
    logger.addHandler(graylog)

    # Return the handler, which may be useful to attach filters to it.
    return graylog
