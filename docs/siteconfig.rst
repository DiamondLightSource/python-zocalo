=============
Configuration
=============

Zocalo will need to be customised for your specific installation to control
aspects such as the settings for the underlying messaging framework, centralised
logging, and more.

To achieve this, Zocalo supports the concept of a site configuration file.
An `example configuration file`_ is included in the Zocalo repository.

Discovery
---------

Zocalo will, by default, look for the main configuration file at the location
specified in the environment variable ``ZOCALO_CONFIG``.

You can also specify locations directly if you use Zocalo programmatically, eg.::

    import zocalo.configuration
    zc = zocalo.configuration.from_file("/alternative/configuration.yml")

or you can load configurations from a `YAML`_ string::

    zc = zocalo.configuration.from_string("version: 1\n\n...")

Configuration file format
-------------------------

The configuration file is in `YAML`_ format. If you are not familiar with YAML
then this `YAML primer`_ may prove useful.

This documentation describes version 1 of the configuration file format. There
is currently no other version. Every site configuration file must declare its
version by including, at the top level:

.. code-block:: yaml

   version: 1

Beyond the version specification every configuration file can contain three
different types of blocks:

#. plugin configurations
#. environment definitions
#. references to further configuration files

Let's look at them individually.

Plugin configurations
---------------------

Each plugin configuration block follows this basic format:

.. code-block:: yaml

   some-unique-name:
       plugin: plugin-name
       ...

The name of the plugin configuration blocks (``some-unique-name``) can be
chosen freely, and their only restriction is that they should not collide
with the names of other blocks that you configure -- otherwise the previous
definition will be overwritten.

The name of the plugin (``plugin-name``) on the other hand refers to a specific
Zocalo configuration plugin.
Through the magic of `Python entry points`_ the list of potentially available
plugins is infinite, and you can easily develop and distribute your own,
independently from Zocalo.

Just because a plugin configuration exists does not mean that it is *active*.
For this you will need to add the configuration to an environment and activate
this environment (see below under :ref:`environments`).

The configuration file may also include configurations for plugins that are
not installed. This will raise a warning when you try to enable such a plugin
configuration, but it will not cause the rest of the configuration to crash
and burn.

Zocalo already includes a few basic plugins, and others may be available to
you via other Python packages, such as `workflows`_. A few of the included
plugins are detailed here:

Storage plugin
^^^^^^^^^^^^^^

tbd.

Logging plugin
^^^^^^^^^^^^^^

This plugin allows site-wide logging configuration. For example:

.. code-block:: yaml

   some-unique-name:
       plugin: logging
       loggers:
         zocalo:
           level: WARNING
         workflows:
           level: WARNING
       verbose:
         - loggers:
             zocalo:
               level: INFO
         - loggers:
             zocalo:
               level: DEBUG
             workflows:
               level: DEBUG

would set the Python loggers ``zocalo`` and ``workflows`` to only report
messages of level ``WARNING`` and above. Apart from the additional
``plugin:``- and ``verbose:``-keys the syntax follows the
`Python Logging Configuration Schema`_. This allows not only the setting of
log levels, but also the definition of log handlers, filters, and formatters.

A plugin definition will, by default, overwrite any previous logging
configuration. While it is fundamentally possible to combine multiple
configurations (using the ``incremental`` key), this will cause all sorts of
problems and is therefore strongly discouraged.

Please note that Zocalo commands will currently always add a handler to log
to the console. This behaviour may be reviewed in the future.

The Zocalo configuration object exposes a facility to read out and increase
a verbosity level, which will apply incremental changes to the logging
configuration. In the above example setting ``zc.logging.verbosity = 1``
would change the log level for ``zocalo`` to ``INFO`` while leaving
``workflows`` at ``WARNING``. Setting ``zc.logging.verbosity = 2`` would
change both to ``DEBUG``.

Note that the verbosity level cannot be decreased, and due to the Python
Logging model verbosity changes should be done close to the initial logging
setup, as otherwise child loggers may have been set up inheriting previous
settings.

The logging plugin offers two Graylog handlers (``GraylogUDPHandler``,
``GraylogTCPHandler``). These are based on `graypy`_, but offer slightly
improved performance by front-loading DNS lookups and apply a patch to
``graypy`` to ensure syslog levels are correctly reported to Graylog.
To use these handlers you can declare them as follows:

.. code-block:: yaml

   some-unique-name:
       plugin: logging
       handlers:
         graylog:
           (): zocalo.configuration.plugin_logging.GraylogUDPHandler
           host: example.com
           port: 1234
       root:
         handlers: [ graylog ]

The logging plugin offers a log filter (``DowngradeFilter``), which can
be attached to loggers to reduce the severity of messages. It takes two
parameters, ``reduce_to`` (default: ``WARNING``) and ``only_below``
(default: ``CRITICAL``), and messages with a level between ``reduce_to``
and ``only_below`` have their log level changed to ``reduce_to``:

.. code-block:: yaml

   some-unique-name:
       plugin: logging
       filters:
         downgrade_all_warnings_and_errors:
           (): zocalo.configuration.plugin_logging.DowngradeFilter
           reduce_to: INFO
       loggers:
         pika:
           filters: [ downgrade_all_warnings_and_errors ]

Graylog plugin
^^^^^^^^^^^^^^

This should be considered deprecated and will be removed at some point in the
future. Use the Logging plugin instead.

.. _environments:

Environment definitions
-----------------------

.. code-block:: yaml

  environments:
    env-name:
      plugins:
        - some-unique-name
        - ...

Environments aggregate multiple plugin configuration blocks together, and
environments are what you load to set up specific plugin configurations.
The environment names (``env-name``) can again be chosen freely. Underneath
environments you can optionally declare groups (here: ``plugins``). These
groups affect the order in which the plugin configurations take effect, and
they also play a role when a configuration file is split up across multiple
files. If you don't specify a group name then the default group name
``plugins`` is used.

Groups are loaded alphabetically, with one exception: ``plugins`` is special
and is always loaded last. Within each group the plugin configurations are
loaded in the specified order.

A special environment name is ``default``, which is the environment that will
be loaded if no other environment is loaded. You can use aliasing (see below
under :ref:`environment_aliases`) to point ``default`` to a different, more
self-explanatory environment name.

.. _environment_aliases:

Environment aliases
^^^^^^^^^^^^^^^^^^^

You can create aliases for environment names by just giving the name of the
underlying environment name. You can only do pure aliasing here, you can not
override parts of the referenced environment at this time.

This configuration gives you an ``alias`` environment, that is exactly
identical to the environment named ``real``:

.. code-block:: yaml

  environments:
    real:
      plugins:
        - ...
    alias: real

Aliases are resolved immediately when they are encountered. The aliased
environment therefore has to be specified in the same configuration file.


References to further files
---------------------------

tbd.

========================
Writing your own plugins
========================

tbd.

.. _Python Logging Configuration Schema: https://docs.python.org/3/library/logging.config.html#dictionary-schema-details
.. _Python entry points: https://amir.rachum.com/blog/2017/07/28/python-entry-points/
.. _YAML primer: https://getopentest.org/reference/yaml-primer.html
.. _YAML: https://en.wikipedia.org/wiki/YAML
.. _example configuration file: https://github.com/DiamondLightSource/python-zocalo/blob/main/contrib/site-configuration.yml
.. _graypy: https://pypi.org/project/graypy/
.. _workflows: https://github.com/DiamondLightSource/python-workflows/tree/main/src/workflows/util/zocalo
