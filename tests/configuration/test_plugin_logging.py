from __future__ import annotations

import logging
from unittest import mock

import pytest

import zocalo.configuration
import zocalo.configuration.plugin_logging

sample_configuration = """
version: 1

logsetup:
  plugin: logging

  handlers:
    graylog:
      (): zocalo.configuration.plugin_logging.GraylogUDPHandler
      host: example.com
      port: 1234

  root:
    level: WARNING
    handlers: [ graylog ]

  loggers:
    zocalo:
      level: INFO
    dials:
      level: INFO
    pika:
      level: WARNING

  verbose:
    - loggers:
        dials:
          level: DEBUG
        pika:
          level: INFO

    - loggers:
        pika:
          level: DEBUG

environments:
  live:
    - logsetup
"""


@mock.patch("zocalo.configuration.plugin_logging.logging")
def test_plugin_sets_up_logging_with_variable_verbosity(logging):
    zc = zocalo.configuration.from_string(sample_configuration)
    logging.config.dictConfig.assert_not_called()
    assert zc.logging is None

    zc.activate_environment("live")
    logging.config.dictConfig.assert_called_once_with(
        {
            "disable_existing_loggers": False,
            "handlers": {
                "graylog": {
                    "()": "zocalo.configuration.plugin_logging.GraylogUDPHandler",
                    "host": "example.com",
                    "port": 1234,
                }
            },
            "incremental": False,
            "loggers": {
                "dials": {"level": "INFO"},
                "pika": {"level": "WARNING"},
                "zocalo": {"level": "INFO"},
            },
            "root": {"handlers": ["graylog"], "level": "WARNING"},
            "verbose": mock.ANY,
            "version": 1,
        }
    )
    assert zc.logging.verbosity == 0

    logging.config.reset_mock()
    logging.config.dictConfig.assert_not_called()

    zc.logging.verbosity = 1

    logging.config.dictConfig.assert_called_once_with(
        {
            "incremental": True,
            "loggers": {"dials": {"level": "DEBUG"}, "pika": {"level": "INFO"}},
            "version": 1,
        }
    )
    assert zc.logging.verbosity == 1

    logging.config.reset_mock()
    logging.config.dictConfig.assert_not_called()

    # Verbosity can't be reduced
    zc.logging.verbosity = 0
    assert zc.logging.verbosity == 1
    logging.config.dictConfig.assert_not_called()

    zc.logging.verbosity = 1
    assert zc.logging.verbosity == 1
    logging.config.dictConfig.assert_not_called()

    # Verbosity can't be increased beyond maximum
    zc.logging.verbosity = 7
    logging.config.dictConfig.assert_called_once_with(
        {"incremental": True, "loggers": {"pika": {"level": "DEBUG"}}, "version": 1}
    )
    assert zc.logging.verbosity == 2


@pytest.mark.parametrize("protocol", ("UDP", "TCP"))
@mock.patch("zocalo.configuration.plugin_logging.graypy")
@mock.patch("zocalo.configuration.plugin_logging.graypy.handler")
@mock.patch("zocalo.configuration.plugin_logging.socket")
def test_graypy_handlers_are_set_up_correctly(socket, handler, graypy, protocol):
    graypy_handler = getattr(graypy, f"GELF{protocol}Handler")
    zocalo_handler = getattr(
        zocalo.configuration.plugin_logging, f"Graylog{protocol}Handler"
    )

    graypy_handler.assert_not_called()
    socket.gethostbyname.assert_not_called()

    h = zocalo_handler(host=mock.sentinel.host, port=mock.sentinel.port)

    socket.gethostbyname.assert_called_once_with(mock.sentinel.host)
    graypy_handler.assert_called_once_with(
        socket.gethostbyname.return_value, mock.sentinel.port, level_names=True
    )
    assert h == graypy_handler.return_value


@mock.patch("zocalo.configuration.plugin_logging.logging")
def test_incremental_configuration_with_handler_definition_is_rejected(logging):
    zc = zocalo.configuration.from_string(
        """
version: 1

logsetup:
  plugin: logging

  handlers:
    graylog:
      (): zocalo.configuration.plugin_logging.GraylogUDPHandler
      host: example.com
      port: 1234

  incremental: True

  root:
    level: WARNING
    handlers: [ graylog ]

environments:
  live:
    - logsetup
"""
    )
    with pytest.raises(zocalo.ConfigurationError, match="incremental"):
        zc.activate_environment("live")


@mock.patch("zocalo.configuration.plugin_logging.logging")
def test_configuration_with_incremental_verbosity_definition_and_handler_is_rejected(
    logging,
):
    zc = zocalo.configuration.from_string(
        """
version: 1

logsetup:
  plugin: logging

  handlers:
    graylog:
      (): zocalo.configuration.plugin_logging.GraylogUDPHandler
      host: example.com
      port: 1234

  verbose:
    - root:
        level: WARNING
        handlers: [ graylog ]

environments:
  live:
    - logsetup
"""
    )
    with pytest.raises(zocalo.ConfigurationError, match="verbosity.*incremental"):
        zc.activate_environment("live")


@mock.patch("zocalo.configuration.plugin_logging.logging")
def test_configuration_with_invalid_verbosity_definitions_is_rejected(logging):
    zc = zocalo.configuration.from_string(
        """
version: 1

logsetup:
  plugin: logging

  verbose:
    - DEBUG

environments:
  live:
    - logsetup
"""
    )
    with pytest.raises(zocalo.ConfigurationError, match="not a dictionary"):
        zc.activate_environment("live")


def test_downgrade_filter_downgrades_log_messages():
    record = logging.LogRecord(
        "some.logger", logging.ERROR, "path", 10, "msg", (), None
    )

    f = zocalo.configuration.plugin_logging.DowngradeFilter(
        "WARNING", only_below="CRITICAL"
    )
    f.filter(record)

    assert record.levelname == "WARNING"
    assert record.levelno == logging.WARNING


def test_downgrade_filter_leaves_low_level_messages_alone():
    record = logging.LogRecord("some.logger", logging.INFO, "path", 10, "msg", (), None)

    f = zocalo.configuration.plugin_logging.DowngradeFilter(
        "WARNING", only_below="CRITICAL"
    )
    f.filter(record)

    assert record.levelname == "INFO"
    assert record.levelno == logging.INFO


def test_downgrade_filter_leaves_high_level_messages_alone():
    record = logging.LogRecord(
        "some.logger", logging.CRITICAL, "path", 10, "msg", (), None
    )

    f = zocalo.configuration.plugin_logging.DowngradeFilter(
        "WARNING", only_below="CRITICAL"
    )
    f.filter(record)

    assert record.levelname == "CRITICAL"
    assert record.levelno == logging.CRITICAL
