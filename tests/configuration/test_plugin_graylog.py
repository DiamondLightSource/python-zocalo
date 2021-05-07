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


def test_plugin_is_available():
    zc = zocalo.configuration.from_string(sample_configuration)
    with pytest.raises(NotImplementedError):
        zc.activate_environment("live")


def test_invalid_configuration_is_rejected():
    with pytest.raises(RuntimeError, match="TCP"):
        zocalo.configuration.from_string(sample_configuration.replace("UDP", "banana"))
