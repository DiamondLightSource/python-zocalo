"""Tests related to graylog functionality."""


from __future__ import annotations

from unittest import mock

import pytest

import zocalo


@mock.patch("zocalo.logging")
@mock.patch("zocalo.graypy")
def test_that_graypy_is_correctly_initialised(graypy, logging):
    with pytest.deprecated_call():
        zocalo.enable_graylog(host="127.0.0.2", port=mock.sentinel.port)
    logging.getLogger.return_value.addHandler.assert_called_once_with(
        graypy.GELFUDPHandler.return_value
    )
    graypy.GELFUDPHandler.assert_called_once()
    assert graypy.GELFUDPHandler.call_args[0] == ("127.0.0.2", mock.sentinel.port)


@mock.patch("zocalo.logging")
@mock.patch("zocalo.graypy")
def test_that_graypy_is_using_sensible_defaults(graypy, logging):
    with pytest.deprecated_call():
        zocalo.enable_graylog(cache_dns=False)
    graypy.GELFUDPHandler.assert_called_once()
    call_args = graypy.GELFUDPHandler.call_args[0]
    assert len(call_args) == 2
    assert "diamond" in call_args[0]
    assert isinstance(call_args[1], int) and call_args[1] > 0


@mock.patch("zocalo.logging")
@mock.patch("zocalo.graypy")
def test_that_the_hostname_is_resolved(graypy, logging):
    with pytest.deprecated_call():
        zocalo.enable_graylog(host="github.com")
    graypy.GELFUDPHandler.assert_called_once()
    call_args = graypy.GELFUDPHandler.call_args[0]
    assert len(call_args) == 2
    assert "github" not in call_args[0]


@mock.patch("zocalo.logging")
@mock.patch("zocalo.graypy")
def test_that_python_log_levels_are_translated_to_graylog_levels(graypy, logging):
    with pytest.deprecated_call():
        zocalo.enable_graylog(cache_dns=False)
    assert graypy.handler.SYSLOG_LEVELS.get(10, None) == 7
    assert graypy.handler.SYSLOG_LEVELS.get(42, 20) == 3
    assert graypy.handler.SYSLOG_LEVELS.get(100, "banana") == 1
