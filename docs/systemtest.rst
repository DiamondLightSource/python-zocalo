============
System Tests
============

Test various parts of the zocalo system. Tests are found via the `zocalo.system_tests` 
entry points. ActiveMQ and Dispatcher tests are included by default.

.. code-block::

    zocalo.run_system_tests (--debug)

Minimum config required to test:

* `ActiveMQ`
* `Dispatcher`

.. code-block::

    storage:
        plugin: storage

        system_tests:
            temp_dir: /tmp/zocalo-test

            dispatcher:
                ispyb_dcid: 1
                expected_beamline: bl

`recipes/test-dispatcher.json` needs to be copied to the local recipe path
