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

Graylog plugin
^^^^^^^^^^^^^^

tbd.

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


References to further files
---------------------------

tbd.

========================
Writing your own plugins
========================

tbd.

.. _example configuration file: https://github.com/DiamondLightSource/python-zocalo/blob/main/contrib/site-configuration.yml
.. _workflows: https://github.com/DiamondLightSource/python-workflows/tree/main/src/workflows/util/zocalo
.. _YAML: https://en.wikipedia.org/wiki/YAML
.. _YAML primer: https://getopentest.org/reference/yaml-primer.html
.. _Python entry points: https://amir.rachum.com/blog/2017/07/28/python-entry-points/
