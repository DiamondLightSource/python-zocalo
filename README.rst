======
Zocalo
======


.. image:: https://img.shields.io/pypi/v/zocalo.svg
        :target: https://pypi.python.org/pypi/zocalo
        :alt: PyPI release

.. image:: https://img.shields.io/conda/vn/conda-forge/zocalo.svg
        :target: https://anaconda.org/conda-forge/zocalo
        :alt: Conda version

.. image:: https://dev.azure.com/zocalo/python-zocalo/_apis/build/status/DiamondLightSource.python-zocalo?branchName=main
        :target: https://dev.azure.com/zocalo/python-zocalo/_build/latest?definitionId=2&branchName=main
        :alt: Build status

.. image:: https://img.shields.io/lgtm/grade/python/g/DiamondLightSource/python-zocalo.svg?logo=lgtm&logoWidth=18
        :target: https://lgtm.com/projects/g/DiamondLightSource/python-zocalo/context:python
        :alt: Language grade: Python

.. image:: https://img.shields.io/lgtm/alerts/g/DiamondLightSource/python-zocalo.svg?logo=lgtm&logoWidth=18
        :target: https://lgtm.com/projects/g/DiamondLightSource/python-zocalo/alerts/
        :alt: Total alerts

.. image:: https://readthedocs.org/projects/zocalo/badge/?version=latest
        :target: https://zocalo.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation status

.. image:: https://img.shields.io/pypi/pyversions/zocalo.svg
        :target: https://pypi.org/project/zocalo/
        :alt: Supported Python versions

.. image:: https://flat.badgen.net/dependabot/DiamondLightSource/python-zocalo?icon=dependabot
        :target: https://github.com/DiamondLightSource/python-zocalo/pulls
        :alt: Dependabot dependency updates

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
        :target: https://github.com/ambv/black
        :alt: Code style: black

.. image:: https://img.shields.io/pypi/l/zocalo.svg
        :target: https://pypi.python.org/pypi/zocalo
        :alt: BSD license

Infrastructure components for automated data processing at Diamond Light Source.

Zocalo is an automated data processing system designed at Diamond Light Source.

The idea of Zocalo is a simple one - to build a messaging framework, where text-based messages are sent between parts of the system to coordinate data analysis. In the wider scope of things this also covers things like archiving, but generally it is handling everything that happens after data aquisition.

Zocalo as a wider whole is made up of two repositories (plus some private internal repositories when deployed at Diamond):

* `DiamondLightSource/python-zocalo <https://github.com/DiamondLightSource/python-zocalo>`_ - Infrastructure components for automated data processing, developed by Diamond Light Source. The package is available through `PyPi <https://pypi.org/project/zocalo/>`_ and `conda-forge <https://anaconda.org/conda-forge/zocalo>`_.
* `DiamondLightSource/python-workflows <https://github.com/DiamondLightSource/python-workflows/>`_ - Zocalo is built on the workflows package. It shouldn't be necessary to interact too much with this package, as the details are abstracted by Zocalo. workflows controls the logic of how services connect to each other and what a service is, and actually send the messages to a message broker. Currently this is an ActiveMQ_ broker (via STOMP_) but support for a RabbitMQ_ broker (via pika_) is being added. Also on `PyPi <https://pypi.org/project/workflows/>`_ and `conda-forge <https://anaconda.org/conda-forge/workflows>`_.

As mentioned, Zocalo is currently built on top of ActiveMQ. ActiveMQ is an apache project that provides a `message broker <https://en.wikipedia.org/wiki/Message_broker>`_ server, acting as a central dispatch that allows various services to communicate. Messages are plaintext, but from the Zocalo point of view it's passing aroung python objects (json dictionaries). Every message sent has a destination to help the message broker route. Messages may either be sent to a specific queue or broadcast to multiple queues. These queues are subscribed to by the services that run in Zocalo. In developing with Zocalo, you may have to interact with ActiveMQ or RabbitMQ, but it is unlikely that you will have to configure it.

Zocalo allows for the monitoring of jobs executing ``python-workflows`` services or recipe wrappers. The ``python-workflows`` package contains most of the infrastructure required for the jobs themselves and more detailed documentation of its components can be found `here <https://github.com/DiamondLightSource/python-workflows/>`_. These components are schematically represented below.

.. image:: ./zocalo/zocalo_graphic.jpg

``python-workflows`` interfaces directly with an externally provided client library for a message broker such as ActiveMQ or RabbitMQ through its ``transport`` module. Services then take messages, process them, and maybe produce some output. The outputs of services can be piped together through a recipe. Services can also be used to monitor message queues. ``python-zocalo`` runs ``python-workflows`` services and recipes, wrapping them so that they are all visible to Zocalo.

.. _ActiveMQ: http://activemq.apache.org/
.. _STOMP: https://stomp.github.io/
.. _RabbitMQ: https://www.rabbitmq.com/
.. _pika: https://github.com/pika/pika


* Documentation: https://zocalo.readthedocs.io.

Features
--------

* TODO

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
