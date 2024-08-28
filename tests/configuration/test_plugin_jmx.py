from __future__ import annotations

import pytest

import zocalo.configuration

sample_configuration = """
version: 1

example:
  plugin: jmx
  host: localhost
  port: 8080
  base_url: /somewhere
  username: admin
  password: admin

environments:
  live:
    - example
"""


def test_plugin_makes_jmx_config_available():
    zc = zocalo.configuration.from_string(sample_configuration)
    assert zc.jmx is None
    zc.activate_environment("live")
    assert isinstance(zc.jmx, dict)
    assert zc.jmx["host"] == "localhost"


def test_invalid_configuration_is_rejected():
    with pytest.raises(zocalo.ConfigurationError, match="integer"):
        zocalo.configuration.from_string(sample_configuration.replace("8080", "banana"))

    with pytest.raises(zocalo.ConfigurationError, match="username"):
        zocalo.configuration.from_string(
            """
            version: 1
            failure:
              plugin: jmx
            """
        )
