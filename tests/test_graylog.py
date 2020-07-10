"""Tests related to graylog functionality."""


import mock
import zocalo


@mock.patch("zocalo.logging")
@mock.patch("zocalo.graypy")
def test_that_graypy_is_correctly_initialised(graypy, logging):
    zocalo.enable_graylog(host=mock.sentinel.host, port=mock.sentinel.port)
    logging.getLogger.return_value.addHandler.assert_called_once_with(
        graypy.GELFUDPHandler.return_value
    )
    graypy.GELFUDPHandler.assert_called_once()
    assert graypy.GELFUDPHandler.call_args[0] == (
        mock.sentinel.host,
        mock.sentinel.port,
    )


@mock.patch("zocalo.logging")
@mock.patch("zocalo.graypy")
def test_that_graypy_is_using_sensible_defaults(graypy, logging):
    zocalo.enable_graylog()
    graypy.GELFUDPHandler.assert_called_once()
    call_args = graypy.GELFUDPHandler.call_args[0]
    assert len(call_args) == 2
    assert "diamond" in call_args[0]
    assert isinstance(call_args[1], int) and call_args[1] > 0


@mock.patch("zocalo.logging")
@mock.patch("zocalo.graypy")
def test_that_python_log_levels_are_translated_to_graylog_levels(graypy, logging):
    zocalo.enable_graylog()
    assert graypy.handler.SYSLOG_LEVELS.get(10, None) == 7
    assert graypy.handler.SYSLOG_LEVELS.get(42, 20) == 3
    assert graypy.handler.SYSLOG_LEVELS.get(100, "banana") == 1
