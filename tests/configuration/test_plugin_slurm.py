from __future__ import annotations

import pytest
import zocalo.configuration

sample_configuration = """
version: 1

example:
  plugin: slurm
  url: http://example.com
  api_version: v0.0.40

example-with-username-and-token:
  plugin: slurm
  url: http://example.com:1234
  user: admin
  user_token: sometoken
  api_version: v0.0.40

environments:
  live:
    - example
  other:
    - example-with-username-and-token
"""


invalid_configuration = """
version: 1

invalid-example:
  plugin: slurm
  user: foo

environments:
  live:
    - invalid-example
"""


def test_without_username():
    zc = zocalo.configuration.from_string(sample_configuration)
    assert zc.slurm is None
    zc.activate_environment("live")
    assert isinstance(zc.slurm, dict)
    assert zc.slurm["url"] == "http://example.com"
    assert "user" not in zc.slurm
    assert zc.slurm["api_version"] == "v0.0.40"


def test_with_username():
    zc = zocalo.configuration.from_string(sample_configuration)
    assert zc.slurm is None
    zc.activate_environment("other")
    assert isinstance(zc.slurm, dict)
    assert zc.slurm["url"] == "http://example.com:1234"
    assert zc.slurm["user"] == "admin"
    assert zc.slurm["api_version"] == "v0.0.40"


def test_user_token_from_external_file(tmp_path):
    user_token = "abcdefg"
    user_token_file = tmp_path / "slurm-user-token"
    user_token_file.write_text(user_token)
    configuration = f"""
version: 1

example:
  plugin: slurm
  url: http://example.com
  api_version: v0.0.40
  user_token: {user_token_file}

environments:
  live:
    - example
"""
    zc = zocalo.configuration.from_string(configuration)
    assert zc.slurm is None
    zc.activate_environment("live")
    assert isinstance(zc.slurm, dict)
    assert zc.slurm["user_token"] == str(user_token_file)


def test_invalid_config():
    with pytest.raises(
        zocalo.ConfigurationError, match="Missing data for required field."
    ):
        zocalo.configuration.from_string(invalid_configuration)
