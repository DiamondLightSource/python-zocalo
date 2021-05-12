=============
Configuration
=============

Zocalo will need to be customised for your specific installation to control
aspects such as the settings for the underlying messaging framework, centralised
logging, and more.

To achieve this, Zocalo supports the concept of a site configuration file
in the `YAML`_ format.

Discovery
---------

Zocalo will, by default, look for the main configuration file at the location
specified in the environment variable ``ZOCALO_CONFIG``.

You can also specify locations directly if you use Zocalo programmatically, eg.::

    import zocalo.configuration
    zc = zocalo.configuration.from_file("/alternative/configuration.yml")

or you can load configurations from a `YAML`_ string::

    zc = zocalo.configuration.from_string("version: 1\n\n...")

.. _YAML: https://en.wikipedia.org/wiki/YAML
