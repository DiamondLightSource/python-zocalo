=======
History
=======

Unreleased
----------

0.32.0 (2024-04-05)
-------------------
* Upgrade to Slurm REST API v0.0.40. (`#248 <https://github.com/DiamondLightSource/python-zocalo/pull/248>`_)
* ``zocalo.configure_rabbitmq``: Show explicit error when VHost not created. (`#241 <https://github.com/DiamondLightSource/python-zocalo/pull/241>`_).

0.30.2 (2023-09-06)
-------------------
* Add the slurm "prefer" field to ``slurm.models.JobProperties``. (`#244 <https://github.com/DiamondLightSource/python-zocalo/pull/244>`_)
* Switch zocalo to pyproject.toml, and update CI. (`#243 <https://github.com/DiamondLightSource/python-zocalo/pull/243>`_)

0.30.1 (2023-08-24)
-------------------
* Fix dependency declaration for pydantic to constrain maximum version.

0.30.0 (2023-06-26)
-------------------
* ``zocalo.configure_rabbitmq``: non-zero exit code on ``HTTPError``

0.29.0 (2023-06-02)
-------------------
* Expose ``url``, ``version``, ``user_name`` and ``user_token`` attributes on ``SlurmRestApi`` instances
* Load ``user_token`` from external file in ``SlurmRestApi`` rather than in the ``zocalo.configuration`` Slurm plugin to allow token changes to be picked up without re-loading ``zocalo.configuration``

0.28.0 (2023-03-20)
-------------------
* Add minimal wrapper for the Slurm REST API to allow job submission
* Add Slurm ``zocalo.configuration`` plugin

0.27.0 (2023-03-16)
-------------------
* Add Dockerfile and build-and-push-docker-image GitHub workflow
* Add ``zocalo.pickup`` command for re-submitting messages stored in the ``zocalo.go.fallback_location`` while the message broker is unavailable

0.26.0 (2022-11-04)
-------------------
* Add dispatcher service
* Add support for Python 3.11

0.25.1 (2022-10-19)
-------------------
* ``JSONLines`` service: trigger ``process_messages`` immediately when reaching 100 stored messages

0.25.0 (2022-10-13)
-------------------
* Add ``JSONLines`` service for appending messages to a file in jsonlines format

0.24.2 (2022-10-04)
-------------------
* ``zocalo.configure_rabbitmq`` cli: downgrade "No matching queue found" error to warning

0.24.1 (2022-08-24)
-------------------
* ``zocalo.configure_rabbitmq`` cli: additional debugging output in event of rare ``IndexError``

0.24.0 (2022-08-17)
-------------------
* ``zocalo.configure_rabbitmq`` cli: enable configuration of vhosts

0.23.0 (2022-08-02)
-------------------
* Remove deprecated ``zocalo.enable_graylog()`` function
* Use ``LoggingAdapter`` to append ``recipe_ID`` to wrapper logs.
  This was inadvertantly broken for the logging plugin added in #176.
  Derived wrappers should now use self.log rather than instantiating
  a logger directly.

0.22.0 (2022-07-12)
-------------------
* ``zocalo.wrapper``: Enable access to ``zocalo.configuration`` object through ``BaseWrapper.config`` attribute
* ``zocalo.configure_rabbitmq`` cli: check response status codes to catch failed API calls
* ``zocalo.configure_rabbitmq`` cli: don't set x-single-active-consumer for streams

0.21.0 (2022-06-28)
-------------------
* ``zocalo.configure_rabbitmq`` cli: require passing user config
  via explicit ``--user-config`` parameter
* ``zocalo.configure_rabbitmq`` cli: optionally disable implicit
  dlq creation via ``dead-letter-queue-create: false``

0.20.0 (2022-06-17)
-------------------
* ``zocalo.configure_rabbitmq`` cli: require explicit
  `dead-letter-routing-key-pattern` when requesting
  creation of a DLQ for a given queue.

0.19.0 (2022-05-24)
-------------------
* ``zocalo.configure_rabbitmq`` cli: advanced binding configuration

0.18.0 (2022-04-12)
-------------------
* Added a logging configuration plugin to comprehensively
  configure logging across applications.

0.17.0 (2022-03-03)
-------------------
* ``zocalo.configure_rabbitmq`` cli:
    * Support for explicitly declaring exchanges
    * Allow queues to bind to more than one exchange

0.16.0 (2022-02-21)
-------------------
* Add ``Mailer`` service for sending email notifications.
  Subscribes to the ``mailnotification`` queue. SMTP settings are specified
  via the ``smtp`` plugin in ``zocalo.configuration``.

0.15.0 (2022-02-16)
-------------------
* Fix for getting user information from the RabbitMQ management API
* Major changes to the RabbitMQ configuration command line tool.
  Users are now updated and deleted, and the tool now understands
  zocalo environment parameters. Configuration files are now
  mandatory, and the ``--seed`` parameter has been removed.

0.14.0 (2021-12-14)
-------------------
* ``zocalo.dlq_purge`` offers a ``--location`` flag to override where files are
  being written
* ``zocalo.dlq_reinject`` can again understand ``zocalo.dlq_purge`` output
  passed on stdin
* Reinjected messages now carry a ``dlq-reinjected: True`` header field

0.13.0 (2021-12-01)
-------------------
* ``zocalo.queue_drain`` now allows the automatic determination
  of destination queues for recipe messages
* ``zocalo.queue_drain`` fixed for use in a RabbitMQ environment
* ``zocalo.dlq_purge`` fixed for use in a RabbitMQ environment
* New functions in ``zocalo.util`` to easily annotate log messages
  with system context information

0.12.0 (2021-11-15)
-------------------
* Add support for queue/exchange bindings to ``RabbitMQAPI``
* Drop support for Python 3.6 and 3.7

0.11.1 (2021-11-08)
-------------------
* Add a RabbitMQ HTTP API in ``zocalo.util.rabbitmq``

0.11.0 (2021-11-03)
-------------------
* Add command line tools for handling dead-letter messages
* ``zocalo.dlq_check`` checks dead-letter queues for messages
* ``zocalo.dlq_purge`` removes messages from specified DLQs and dumps them to a directory
  specified in the Zocalo configuration
* ``zocalo.dlq_reinject`` takes a serialised message produced by ``zocalo.dlq_purge`` and
  places it back on a queue
* Use ``argparse`` for all command line tools and make use of ``workflows`` transport
  argument injection. Minimum ``workflows`` version is now 2.14
* New ``zocalo.util.rabbitmq.RabbitMQAPI()`` providing a thin wrapper around the
  RabbitMQ HTTP API

0.10.0 (2021-10-04)
-------------------
* New ``zocalo.shutdown`` command to shutdown Zocalo services
* New ``zocalo.queue_drain`` command to drain one queue into another in a controlled manner
* New ``zocalo.util.rabbitmq.http_api_request()`` utility function to return a
  ``urllib.request.Request`` object to query the RabbitMQ API using the credentials
  specified via ``zocalo.configuration``.
* ``zocalo.wrap`` now emits tracebacks on hard crashes and ``SIGUSR2`` signals

0.9.1 (2021-08-18)
------------------
* Expand ~ in paths in configuration files

0.9.0 (2021-08-18)
------------------
* Removed --live/--test command line arguments, use -e/--environment instead
* zocalo.go, zocalo.service, zocalo.wrap accept -t/--transport command line
  options, and the default can be set via the site configuration.

0.8.1 (2021-07-08)
------------------
* Keep wrapper status threads alive through transport disconnection events

0.8.0 (2021-05-18)
------------------
* Support for Zocalo configuration files

0.7.4 (2021-03-17)
------------------
* Documentation improvements

0.7.3 (2021-01-19)
------------------
* Ignore error when logserver hostname can't be looked up immediately

0.7.2 (2021-01-18)
------------------
* Add a symbolic link handling library function
* Cache the logserver hostname by default

0.7.1 (2020-11-13)
------------------
* Add a --dry-run option to zocalo.go

0.7.0 (2020-11-02)
------------------
* Drop support for Python 3.5
* Update language constructs for Python 3.6+

0.6.4 (2020-11-02)
------------------
* Add support for Python 3.9

0.6.3 (2020-05-25)
------------------
* Remove stomp.py requirement - this is pulled in via workflows only

0.6.2 (2019-07-16)
------------------
* Set live flag in service environment if service started with '--live'

0.6.0 (2019-06-17)
------------------
* Start moving dlstbx scripts to zocalo package:
  * zocalo.go
  * zocalo.wrap
* Entry point 'dlstbx.wrappers' has been renamed 'zocalo.wrappers'
* Dropped Python 3.4 support


0.5.4 (2019-03-22)
------------------
* Compatibility fixes for graypy >= 1.0

0.5.2 (2018-12-11)
------------------
* Don't attempt to load non-existing file


0.5.1 (2018-12-04)
------------------
* Fix packaging bug which meant files were missing from the release


0.5.0 (2018-12-04)
------------------
* Add zocalo.service command to start services


0.4.0 (2018-12-04)
------------------
* Add status notification thread logic


0.3.0 (2018-12-04)
------------------
* Add schlockmeister service and base wrapper class


0.2.0 (2018-11-28)
------------------
* Add function to enable logging to graylog


0.1.0 (2018-10-19)
------------------
* First release on PyPI.
