import os
from unittest import mock

import zocalo.configuration


def test(tmp_path):
    config_file = tmp_path / "configuration.yml"
    with open(config_file, "w") as fh:
        fh.write(
            """
version: 1

recipe_path: /path/to/recipes
dropfile_path: /path/to/dropfiles
dlq: /path/to/dlq

jmx:
  plugin: jmx
  host: localhost
  port: 8161
  base_url: api/jolokia
  username: test
  password: test

graylog:
  plugin: graylog
  protocol: UDP
  host: localhost
  port: 12201

stomp-test:
  plugin: stomp
  host: localhost
  port: 61613
  username: zocalo
  password: zocalo-development
  prefix: zocalo

stomp-live:
  plugin: stomp
  host: prod-zocalo
  port: 61613
  username: zocalo
  password: password
  prefix: zocalo

environments:
  live:
    stomp: stomp-live
  test:
    stomp: stomp-test
"""
        )

    with mock.patch.dict(os.environ, {"ZOCALO_CONFIG": os.fspath(config_file)}):
        zocalo.configuration.load()
