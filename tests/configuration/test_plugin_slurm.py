from __future__ import annotations

import pytest

import zocalo.configuration

sample_configuration = """
version: 1

example:
  plugin: slurm
  url: http://example.com
  api_version: v0.0.36

example-with-username-and-token:
  plugin: slurm
  url: http://example.com:1234
  user: admin
  user_token: sometoken
  api_version: v0.0.36

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
    assert zc.slurm["api_version"] == "v0.0.36"


def test_with_username():
    zc = zocalo.configuration.from_string(sample_configuration)
    assert zc.slurm is None
    zc.activate_environment("other")
    assert isinstance(zc.slurm, dict)
    assert zc.slurm["url"] == "http://example.com:1234"
    assert zc.slurm["user"] == "admin"
    assert zc.slurm["api_version"] == "v0.0.36"


def test_invalid_config():
    with pytest.raises(
        zocalo.ConfigurationError, match="Missing data for required field."
    ):
        zocalo.configuration.from_string(invalid_configuration)
