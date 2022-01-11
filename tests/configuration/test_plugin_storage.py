from __future__ import annotations

import zocalo.configuration

sample_configuration = """
version: 1

some-constants:
  plugin: storage
  this: that
  one: other

empty-plugin:
  plugin: storage

environments:
  some:
    - some-constants
  empty:
    - empty-plugin
  overwrite:
    plugins:
      - constants
      - sane-constants
  nothing: {}

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
"""


def test_assert_plain_configuration_object_does_not_have_storage_attribute():
    zc = zocalo.configuration.from_string(sample_configuration)
    assert zc.storage is None
    zc.activate_environment("nothing")
    assert zc.storage is None


def test_plugin_is_available():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("empty")
    assert zc.storage is not None


def test_simple_plugin_usage():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("some")

    assert zc.storage["this"] == "that"
    assert zc.storage["one"] == "other"


def test_multi_plugin_usage():
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate_environment("overwrite")

    assert len(zc.storage["order"]) == 2
    assert zc.storage["units"] == "metric"
    assert zc.storage["oxford_comma"] is True
