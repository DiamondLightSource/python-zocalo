import os

import pytest

import zocalo.configuration

sample_configuration = """
version: 1

graylog:
  plugin: graylog
  protocol: UDP
  host: localhost
  port: 12201

constants:
  plugin: storage
  order:
    - cream
    - jam
  oxford_comma: undecided

sane-constants:
  plugin: storage
  oxford_comma: yes
  units: metric

environments:
  live:
    plugins:
      - constants
      - sane-constants
  partial:
    plugins:
      - constants
  part-2:
    - sane-constants
  empty: {}
"""


def _assert_configuration_is_empty(zc):
    assert zc.environments == frozenset({})
    assert "0 environments" in str(zc)
    assert "0 plugin configurations" in str(zc)


def test_loading_minimal_valid_configuration():
    zc = zocalo.configuration.from_string("version: 1")
    _assert_configuration_is_empty(zc)


def test_loading_minimal_valid_configuration_from_file(tmp_path):
    config_file = tmp_path.joinpath("config.yml")
    config_file.write_text("version: 1")
    zc = zocalo.configuration.from_file(os.fspath(config_file))
    _assert_configuration_is_empty(zc)
    zc = zocalo.configuration.from_file(config_file)
    _assert_configuration_is_empty(zc)


def test_loading_sample_configuration():
    zc = zocalo.configuration.from_string(sample_configuration)

    assert zc.environments == frozenset({"live", "partial", "part-2", "empty"})
    assert "4 environments" in str(zc)
    assert "3 plugin configurations" in str(zc)


def test_cannot_load_inconsistent_configuration():
    with pytest.raises(RuntimeError):
        zocalo.configuration.from_string(
            """
            version: 1
            environments:
              failure:
                - unreferenced-plugin
            """
        )


def test_cannot_activate_missing_environment():
    zc = zocalo.configuration.from_string("version: 1")
    with pytest.raises(ValueError):
        zc.activate_environment("live")
    assert zc.active_environments == []
    assert "live" not in str(zc)


def test_activate_an_empty_environment():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("empty")
    zc.active_environments.append("list should not be mutable")
    assert zc.active_environments == ["empty"]
    assert "empty" in str(zc)


def test_activate_an_environment():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("live")
    zc.active_environments.append("list should not be mutable")
    assert zc.active_environments == ["live"]
    assert "live" in str(zc)
