from __future__ import annotations

import pytest

import zocalo.configuration

sample_configuration = """
version: 1

my-smtp:
  plugin: smtp
  host: localhost
  port: 8080
  from: foo@example.com

environments:
  live:
    - my-smtp
"""


def test_plugin_makes_smtp_config_available():
    zc = zocalo.configuration.from_string(sample_configuration)
    assert zc.smtp is None
    zc.activate_environment("live")
    assert isinstance(zc.smtp, dict)
    assert zc.smtp["host"] == "localhost"
    assert zc.smtp["port"] == 8080
    assert zc.smtp["from"] == "foo@example.com"


def test_invalid_configuration_is_rejected():
    with pytest.raises(zocalo.ConfigurationError, match="integer"):
        zocalo.configuration.from_string(sample_configuration.replace("8080", "banana"))

    with pytest.raises(zocalo.ConfigurationError, match="host"):
        zocalo.configuration.from_string(
            """
            version: 1
            failure:
              plugin: smtp
            """
        )
