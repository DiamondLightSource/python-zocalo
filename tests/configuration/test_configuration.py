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


def test_cannot_load_unversioned_yaml_files():
    with pytest.raises(RuntimeError, match="Invalid configuration"):
        zocalo.configuration.from_string("value: 1")


def test_cannot_load_unknown_configuration_file_versions():
    with pytest.raises(RuntimeError, match="not understand"):
        zocalo.configuration.from_string("version: 0")


def test_loading_minimal_valid_configuration_from_file(tmp_path):
    config_file = tmp_path.joinpath("config.yml")
    config_file.write_text("version: 1")
    zc = zocalo.configuration.from_file(os.fspath(config_file))
    _assert_configuration_is_empty(zc)
    zc = zocalo.configuration.from_file(config_file)
    _assert_configuration_is_empty(zc)


def test_cannot_load_missing_file(tmp_path):
    with pytest.raises(RuntimeError, match="not found"):
        zocalo.configuration.from_file(tmp_path / "missing.yml")


def test_cannot_load_invalid_file(tmp_path):
    config = tmp_path / "invalid.yml"
    config.write_text("x: y: z:")
    with pytest.raises(RuntimeError, match="invalid.yml"):
        zocalo.configuration.from_file(config)


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


def test_cannot_load_configuration_where_environments_specifies_plugin_as_string():
    with pytest.raises(RuntimeError, match="invalid-spec"):
        zocalo.configuration.from_string(
            """
            version: 1
            environments:
              invalid-spec: constants
            constants:
              plugin: storage
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


def test_activate_one_environment():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("live")
    zc.active_environments.append("list should not be mutable")
    assert zc.active_environments == ["live"]
    assert "live" in str(zc)


def test_activate_multiple_environments():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("partial")
    zc.activate_environment("part-2")
    assert zc.active_environments == ["partial", "part-2"]
    assert "partial" in str(zc)
    assert "part-2" in str(zc)
