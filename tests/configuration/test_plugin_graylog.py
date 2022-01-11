from __future__ import annotations

from unittest import mock

import pytest

import zocalo.configuration

sample_configuration = """
version: 1

graylog:
  plugin: graylog
  protocol: UDP
  host: localhost
  port: 12201

environments:
  live:
    - graylog
"""


@mock.patch("zocalo.configuration.plugin_graylog.graypy")
@mock.patch("zocalo.configuration.plugin_graylog.graypy.handler")
@mock.patch("zocalo.configuration.plugin_graylog.logging")
def test_plugin_sets_up_logging(logging, handler, graypy):
    zc = zocalo.configuration.from_string(sample_configuration)
    graypy.GELFUDPHandler.assert_not_called()
    logging.getLogger.return_value.addHandler.assert_not_called()

    zc.activate_environment("live")
    graypy.GELFUDPHandler.assert_called_once_with("127.0.0.1", 12201, level_names=True)
    relevant_handler = graypy.GELFUDPHandler.return_value
    logging.getLogger.return_value.addHandler.assert_called_once_with(relevant_handler)
    assert zc.graylog == relevant_handler


def test_invalid_configuration_is_rejected():
    with pytest.raises(zocalo.ConfigurationError, match="TCP"):
        zocalo.configuration.from_string(sample_configuration.replace("UDP", "banana"))

    with pytest.raises(zocalo.ConfigurationError, match="host"):
        zocalo.configuration.from_string(
            """
            version: 1
            graylog:
              plugin: graylog
            """
        )
