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

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
        :target: https://github.com/ambv/black
        :alt: Code style: black

.. image:: https://img.shields.io/pypi/l/zocalo.svg
        :target: https://pypi.python.org/pypi/zocalo
        :alt: BSD license

..

        |
        | `M. Gerstel, A. Ashton, R.J. Gildea, K. Levik, and G. Winter, "Data Analysis Infrastructure for Diamond Light Source Macromolecular & Chemical Crystallography and Beyond", in Proc. ICALEPCS'19, New York, NY, USA, Oct. 2019, pp. 1031-1035. <https://doi.org/10.18429/JACoW-ICALEPCS2019-WEMPR001>`_ |DOI|

        .. |DOI| image:: https://img.shields.io/badge/DOI-10.18429/JACoW--ICALEPCS2019--WEMPR001-blue.svg
                :target: https://doi.org/10.18429/JACoW-ICALEPCS2019-WEMPR001
                :alt: Primary Reference DOI

|

Zocalo is an automated data processing system designed at Diamond Light Source. This repository contains infrastructure components for Zocalo.

The idea of Zocalo is a simple one - to build a messaging framework, where text-based messages are sent between parts of the system to coordinate data analysis. In the wider scope of things this also covers things like archiving, but generally it is handling everything that happens after data aquisition.

Zocalo as a wider whole is made up of two repositories (plus some private internal repositories when deployed at Diamond):

* `DiamondLightSource/python-zocalo <https://github.com/DiamondLightSource/python-zocalo>`_ - Infrastructure components for automated data processing, developed by Diamond Light Source. The package is available through `PyPi <https://pypi.org/project/zocalo/>`__ and `conda-forge <https://anaconda.org/conda-forge/zocalo>`__.
* `DiamondLightSource/python-workflows <https://github.com/DiamondLightSource/python-workflows/>`_ - Zocalo is built on the workflows package. It shouldn't be necessary to interact too much with this package, as the details are abstracted by Zocalo. workflows controls the logic of how services connect to each other and what a service is, and actually send the messages to a message broker. Currently this is an ActiveMQ_ broker (via STOMP_) but support for a RabbitMQ_ broker (via pika_) is being added. This is also available on `PyPi <https://pypi.org/project/workflows/>`__ and `conda-forge <https://anaconda.org/conda-forge/workflows>`__.

As mentioned, Zocalo is currently built on top of ActiveMQ. ActiveMQ is an apache project that provides a `message broker <https://en.wikipedia.org/wiki/Message_broker>`_ server, acting as a central dispatch that allows various services to communicate. Messages are plaintext, but from the Zocalo point of view it's passing aroung python objects (json dictionaries). Every message sent has a destination to help the message broker route. Messages may either be sent to a specific queue or broadcast to multiple queues. These queues are subscribed to by the services that run in Zocalo. In developing with Zocalo, you may have to interact with ActiveMQ or RabbitMQ, but it is unlikely that you will have to configure it.

Zocalo allows for the monitoring of jobs executing ``python-workflows`` services or recipe wrappers. The ``python-workflows`` package contains most of the infrastructure required for the jobs themselves and more detailed documentation of its components can be found in the ``python-workflows`` `GitHub repository <https://github.com/DiamondLightSource/python-workflows/>`_ and `the Zocalo documentation <https://zocalo.readthedocs.io>`_. 

.. _ActiveMQ: http://activemq.apache.org/
.. _STOMP: https://stomp.github.io/
.. _RabbitMQ: https://www.rabbitmq.com/
.. _pika: https://github.com/pika/pika

Core Concepts
-------------

There are two kinds of task run in Zocalo: *services* and *wrappers*.
A service should handle a discrete short-lived task, for example a data processing job on a small data packet (e.g. finding spots on a single image in an X-ray crystallography context), or inserting results into a database.
In contrast, wrappers can be used for longer running tasks, for example running data processing programs such as xia2_ or fast_ep_.

* A **service** starts in the background and waits for work. There are many services constantly running as part of normal Zocalo operation. In typical usage at Diamond there are ~100 services running at a time.
* A **wrapper** on the other hand, is only run when needed. They wrap something that is not necessarily aware of Zocalo - e.g. downstream processing software such as xia2 have no idea what zocalo is, and shouldn't have to. A wrapper takes a message, converts to the instantiation of command line, runs the software - typically as a cluster job, then reformats the results into a message to send back to Zocalo. These processes have no idea what Zocalo is, but are being run by a script that handles the wrapping.

At Diamond, everything goes to one service to start with: the **Dispatcher**. This takes the initial request message and attaches useful information for the rest of Zocalo. The implementation of the Dispatcher at Diamond is environment specific and not public, but it does some things that would be useful for a similar service to do in other contexts. At Diamond there is interaction with the `ISPyB database <https://github.com/DiamondLightSource/ispyb-database>`_ that stores information about what is run, metadata, how many images, sample type etc. Data stored in the database influences what software we want to be running and this information might need to be read from the database in many, many services. We obviously don't want to read the same thing from many clients and flood the database, and don't want the database to be a single point of failure. The dispatcher front-loads all the database operations - it takes the data collection ID (DCID) and looks up in ISPyB all the information that could be needed for processing. In terms of movement through the system, it sits between the initial message and the services:

.. code:: bash

        message -> Dispatcher -> [Services]

At end of processing there might be information that needs to go back into the databases, for which Diamond has a special ISPyB service to do the writing. If the DB goes down, that is fine - things will queue up for the ISPyB service and get processed when the database becomes available again, and written to the database when ready. This isolates us somewhat from intermittent failures.

The only public Zocalo service at present is ``Schlockmeister``, a garbage collection service that removes jobs that have been requeued mutliple times. Diamond operates a variety of internal Zocalo services which perform frequently required operations in a data analysis pipeline.

.. _xia2: https://xia2.github.io/
.. _fast_ep: https://github.com/DiamondLightSource/fast_ep

Working with Zocalo
-------------------

`Graylog <https://www.graylog.org/>`_ is used to manage the logs produced by Zocalo. Once Graylog and the message broker server are running then services and wrappers can be launched with Zocalo. 

Zocalo provides some command line tools. These tools are ``zocalo.go``, ``zocalo.wrap`` and ``zocalo.service``: the first triggers the processing of a recipe and the second runs a command while exposing its status to Zocalo so that it can be tracked. Services are available through ``zocalo.service`` if they are linked through the ``workflows.services`` entry point in ``setup.py``. For example, to start a Schlockmeister service:

.. code:: bash

        $ zocalo.service -s Schlockmeister

.. list-table:: 
        :widths: 100
        :header-rows: 1

        * - Q: How are services started?
        * - A: Zocalo itself is agnostic on this point. Some of the services are self-propagating and employ simple scaling behaviour - in particular the per-image-analysis services. The services in general all run on cluster nodes, although this means that they can not be long lived - beyond a couple of hours there is a high risk of the service cluster jobs being terminated or pre-empted. This also helps encourage programming more robust services if they could be killed.

.. list-table:: 
        :widths: 100
        :header-rows: 1

        * - Q: So if a service is terminated in the middle of processing it will still get processed?
        * - A: Yes, messages are handled in transactions - while a service is processing a message, it's marked as "in-progress" but isn't completely dropped. If the service doesn't process the message, or it's connection to ActiveMQ gets dropped, then it get's requeued so that another instance of the service can pick it up.

Repeat Message Failure 
----------------------

How are repeat errors handled? This is a problem with the system - if e.g. an image or malformed message kills a service then it will get requeued, and will eventually kill all instances of the service running (which will get re-spawned, and then die, and so forth).

We have a special service that looks for repeat failures and moves them to a special "Dead Letter Queue". This service is called Schlockmeister_, and is the only service at time of writing that has migrated to the public zocalo repository. This service looks inside the message that got sent, extracts some basic information from the message in as safe a way as possible and repackages to the DLQ with information on what it was working on, and the "history" of where the message chain has been routed.

.. _Schlockmeister: https://github.com/DiamondLightSource/python-zocalo/tree/master/zocalo/service


