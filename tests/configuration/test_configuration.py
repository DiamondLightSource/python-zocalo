import logging
import os
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


def test_return_empty_configuration_if_no_path_specified():
    with mock.patch.dict(os.environ, {"ZOCALO_CONFIG": ""}):
        zc = zocalo.configuration.from_file()
    _assert_configuration_is_empty(zc)


def test_loading_minimal_valid_configuration():
    zc = zocalo.configuration.from_string("version: 1")
    _assert_configuration_is_empty(zc)


def test_cannot_load_unversioned_yaml_files():
    with pytest.raises(zocalo.ConfigurationError, match="Invalid configuration"):
        zocalo.configuration.from_string("value: 1")


def test_cannot_load_unknown_configuration_file_versions():
    with pytest.raises(zocalo.ConfigurationError, match="not understand"):
        zocalo.configuration.from_string("version: 0")


def test_loading_minimal_valid_configuration_from_file(tmp_path):
    config_file = tmp_path.joinpath("config.yml")
    config_file.write_text("version: 1")
    zc = zocalo.configuration.from_file(os.fspath(config_file))
    _assert_configuration_is_empty(zc)
    zc = zocalo.configuration.from_file(config_file)
    _assert_configuration_is_empty(zc)
    with mock.patch.dict(os.environ, {"ZOCALO_CONFIG": os.fspath(config_file)}):
        zc = zocalo.configuration.from_file()
    _assert_configuration_is_empty(zc)


def test_cannot_load_missing_file(tmp_path):
    with pytest.raises(zocalo.ConfigurationError, match="not found"):
        zocalo.configuration.from_file(tmp_path / "missing.yml")


def test_cannot_load_invalid_file(tmp_path):
    config = tmp_path / "invalid.yml"
    config.write_text("x: y: z:")
    with pytest.raises(zocalo.ConfigurationError, match="invalid.yml"):
        zocalo.configuration.from_file(config)


def test_loading_sample_configuration():
    zc = zocalo.configuration.from_string(sample_configuration)

    assert zc.environments == frozenset({"live", "partial", "part-2", "empty"})
    assert "4 environments" in str(zc)
    assert "3 plugin configurations" in str(zc)


def test_cannot_load_inconsistent_configuration():
    with pytest.raises(zocalo.ConfigurationError):
        zocalo.configuration.from_string(
            """
            version: 1
            environments:
              failure:
                - unreferenced-plugin
            """
        )


def test_cannot_load_configuration_where_environments_specifies_plugin_as_string():
    with pytest.raises(zocalo.ConfigurationError, match="invalid-spec"):
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
    assert zc.active_environments == ()
    assert "live" not in str(zc)


def test_activate_an_empty_environment():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("empty")
    assert zc.active_environments == ("empty",)
    assert "empty" in str(zc)


def test_activate_one_environment():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("live")
    assert zc.active_environments == ("live",)
    with pytest.raises(AttributeError):
        zc.active_environments = ("this-should-not-be-writeable",)
    assert "live" in str(zc)


def test_activate_multiple_environments():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("partial")
    zc.activate_environment("part-2")
    assert zc.active_environments == ("partial", "part-2")
    assert "partial" in str(zc)
    assert "part-2" in str(zc)


@pytest.mark.parametrize("name", ("include", "environments", "version"))
def test_environment_can_not_reference_reserved_name(name):
    with pytest.raises(zocalo.ConfigurationError, match="reserved"):
        zocalo.configuration.from_string(
            f"""
            version: 1
            environments:
              test:
                - {name}
            """
        )


def test_unknown_plugin_definition_triggers_a_warning(caplog):
    unique_plugin_name = "testcase_for_an_unknown_plugin"
    with caplog.at_level(logging.WARNING):
        zc = zocalo.configuration.from_string(
            f"""
            version: 1
            undefined-plugin:
              plugin: {unique_plugin_name}
            """
        )
    assert unique_plugin_name in caplog.text
    assert not hasattr(zc, unique_plugin_name)


def test_configuration_can_specify_a_missing_resolution_file(tmp_path):
    zocalo.configuration.from_string(
        f"""
        version: 1
        unused-plugin:
          {tmp_path / 'missing_file'}
        """
    )


@mock.patch("pathlib.io.open")
def test_configuration_can_specify_an_unreadable_resolution_file(mock_open, tmp_path):
    mock_open.side_effect = PermissionError("Access denied to mock file")
    zc = zocalo.configuration.from_string(
        f"""
        version: 1
        forbidden-plugin:
          {tmp_path / 'forbidden_file'}
        environments:
         forbidden:
           - forbidden-plugin
        """
    )
    with pytest.raises(PermissionError):
        zc.activate_environment("forbidden")


def test_plugins_can_be_configured_in_an_external_file(tmp_path):
    external_plugin = tmp_path / "external.yml"
    external_plugin.write_text(
        """
        plugin: storage
        value: sentinel
        """
    )
    zc = zocalo.configuration.from_string(
        f"""
        version: 1
        external:
          {tmp_path / 'external.yml'}
        environments:
          ext:
            - external
        """
    )
    assert "1 of" in str(zc)
    zc.activate_environment("ext")
    assert "1 of" not in str(zc)
    assert zc.storage["value"] == "sentinel"


@pytest.mark.xfail(raises=NotImplementedError, strict=True)
def test_loading_modular_configuration_from_string(tmp_path):
    secondary_file = tmp_path / "config.yml"
    secondary_file.write_text(sample_configuration)

    zc = zocalo.configuration.from_string(
        f"""
        version: 1
        include:
          - {secondary_file}
        """
    )
    assert zc.environments


@pytest.mark.xfail(raises=NotImplementedError, strict=True)
def test_loading_modular_configuration_from_file(tmp_path):
    secondary_file = tmp_path / "config.yml"
    secondary_file.write_text(sample_configuration)
    primary_file = tmp_path / "primary.yml"
    primary_file.write_text(
        f"""
        version: 1
        include:
          - config.yml
        """
    )

    zc = zocalo.configuration.from_file(primary_file)
    assert zc.environments


def test_cannot_load_modular_configuration_with_missing_reference(tmp_path):
    secondary_file = tmp_path / "non-existing-file.yml"

    with pytest.raises(FileNotFoundError):
        zocalo.configuration.from_string(
            f"""
            version: 1
            include:
              - {secondary_file}
            """
        )


def test_cannot_load_modular_configuration_with_broken_reference(tmp_path):
    secondary_file = tmp_path / "invalid.yml"
    secondary_file.write_text("x: y: z:")
    with pytest.raises(zocalo.ConfigurationError, match="invalid.yml"):
        zocalo.configuration.from_string(
            f"""
            version: 1
            include:
              - {secondary_file}
            """
        )
