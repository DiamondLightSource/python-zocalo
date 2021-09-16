Zocalo System Tests
======

```bash
zocalo.test (--debug)
```

Minimum config required to test 
* `activemq`
* `dispatcher`

```yaml
storage:
  plugin: storage

  system_tests:
    temp_dir: /tmp/zocalo-test

    dispatcher:
      ispyb_dcid: 1
      expected_beamline: bl
```

`recipes/test-dispatcher.json` needs to be copied to the local recipe path
