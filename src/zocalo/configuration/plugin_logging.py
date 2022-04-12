from __future__ import annotations

import copy
import logging.config
import socket
from typing import Any

import graypy.handler

import zocalo


def _config_is_incremental(config: dict[str, Any]) -> bool:
    forbidden_keys = {"filters", "formatters", "handlers"}

    # Incremental configurations must not declare any of those
    if any(key in config for key in forbidden_keys):
        return False

    # Incremental configurations must not attach any of those
    # to the root logger
    if any(key in config.get("root", {}) for key in forbidden_keys):
        return False
    # or any other logger
    for logger in config.get("loggers", {}).values():
        if any(key in logger for key in forbidden_keys):
            return False

    return True


class LoggingIncrementer:
    def __init__(self, setup: dict[str, Any]):
        self._setup = setup
        self._verbosity_level = 0

    @property
    def verbosity(self) -> int:
        return self._verbosity_level

    @verbosity.setter
    def verbosity(self, value: int) -> None:
        if value <= self._verbosity_level:
            return
        for verbosity_level in range(self._verbosity_level, value):
            try:
                incremental = self._setup.get("verbose", [])[verbosity_level]
            except IndexError:
                break
            logging.config.dictConfig(incremental)
            self._verbosity_level = verbosity_level + 1

    def __repr__(self) -> str:
        return f"<LoggingConfiguration verbosity={self._verbosity_level}>"


class Logging:
    """
    A plugin to set up consistent logging configuration
    using a Zocalo configuration file.
    """

    @staticmethod
    def activate(configuration: dict) -> LoggingIncrementer:
        logconfig = copy.deepcopy(configuration)

        del logconfig["plugin"]
        logconfig.setdefault("version", 1)
        logconfig.setdefault("disable_existing_loggers", False)
        logconfig.setdefault("incremental", False)

        if logconfig["incremental"] and not _config_is_incremental(logconfig):
            raise zocalo.ConfigurationError(
                "Logging configuration error: definition defines items not allowed "
                "in an incremental definition"
            )

        logging.config.dictConfig(logconfig)

        for level, verbosity_def in enumerate(logconfig.get("verbose", [])):
            if not isinstance(verbosity_def, dict):
                raise zocalo.ConfigurationError(
                    f"Logging configuration error: verbosity level {level+1} definition "
                    "is not a dictionary"
                )
            verbosity_def.setdefault("version", logconfig["version"])
            verbosity_def.setdefault("incremental", True)
            if verbosity_def["incremental"] and not _config_is_incremental(
                verbosity_def
            ):
                raise zocalo.ConfigurationError(
                    f"Logging configuration error: verbosity level {level+1} definition "
                    "defines items not allowed in an incremental definition"
                )

        return LoggingIncrementer(logconfig)


def _monkeypatch_graypy() -> None:
    """
    Monkeypatch a helper class into graypy to support log levels in Graylog.
    This translates Python integer level numbers to syslog levels.
    """

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


def _resolve_hostname(host: str) -> str:
    # Attempt to resolve the hostname only once during setup
    # rather than once for each connection, which is the default behaviour.
    # For a UDP handler the default would mean one lookup per logging call.
    try:
        return socket.gethostbyname(host)
    except Exception:
        return host


def GraylogTCPHandler(*, host: str, port: int) -> logging.Handler:
    """
    A handler factory to enable logging to a Graylog server using graypy via TCP.
    """
    _monkeypatch_graypy()
    return graypy.GELFTCPHandler(_resolve_hostname(host), port, level_names=True)


def GraylogUDPHandler(*, host: str, port: int) -> logging.Handler:
    """
    A handler factory to enable logging to a Graylog server using graypy via UDP.
    """
    _monkeypatch_graypy()
    return graypy.GELFUDPHandler(_resolve_hostname(host), port, level_names=True)


class DowngradeFilter(logging.Filter):
    """
    Reduces the level of a log message within certain boundaries.

    The two thresholds are 'reduce_to' and 'only_below'.

    Messages with a level between 'reduce_to' (default: WARNING) and 'only_below'
    (default: CRITICAL) have their log level changed to 'reduce_to'.

    Messages with a level below the 'reduce_to' threshold, or at or above the
    'only_below' threshold are passed through unchanged.
    """

    def __init__(self, reduce_to: str = "WARNING", *, only_below: str = "CRITICAL"):
        super().__init__()

        self._reduce_to_name = reduce_to
        self._reduce_to_value = logging.getLevelName(reduce_to)
        self._only_below_name = only_below
        self._only_below_value = logging.getLevelName(only_below)

        if self._only_below_value <= self._reduce_to_value:
            raise ValueError(
                f"'reduce_to' ({self._reduce_to_name} = {self._reduce_to_value})"
                " must be smaller than"
                f" 'only_below' ({self._only_below_name} = {self._only_below_value})"
            )

    def __repr__(self) -> str:
        return (
            f"<DowngradeFilter reduce_to={self._reduce_to_name}"
            f" only_below={self._only_below_name}>"
        )

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno <= self._reduce_to_value:
            return True
        if record.levelno >= self._only_below_value:
            return True
        record.levelno = self._reduce_to_value
        record.levelname = self._reduce_to_name
        return True
