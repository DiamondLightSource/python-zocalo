*************
Prerequisites
*************
Zocalo was originally developed at Diamond Light Source, a UK-based synchrotron.
The use case was providing a clear way to run complex jobs on various computing clusters.
Therefore, development of this tool was intertwined with the use of existing software tools.

This page specifies how to set up a development environment which you can later use to test new Zocalo recipes and wrappers.

Packages and repositories
=========================

To develop with Zocalo, the following packages/libraries should be installed locally on your machine:

- Python Zocalo - **this library**, contains the zocalo wrapper class which is used to make a Zocalo job
- `Zocalo <https://gitlab.diamond.ac.uk/scisoft/zocalo>`_ - which stores the recipes in use at Diamond along with some other information on how it is used
- `dlstbx <https://gitlab.diamond.ac.uk/scisoft/mx/dlstbx>`_ - a big module which contains lot of tools for data analysis at Diamond. It also consolidates Zocalo jobs and services and creates an entry point for them
- `Python Workflows <https://github.com/DiamondLightSource/python-workflows>`_ - for making lightweight services in a task oriented environment. Home of the CommonService class used to create Zocalo services

DIALS
----------------

DIALS is a collaborative project for x-ray crystallography tools, which includes the dlstbx tools.
This must be installed to enable wrapper functionality in Zocalo.
Using a local copy of DIALS is also current best practice for Zocalo development.

Detailed installation instructions are given `here
<https://dials.github.io/installation.html>`_.

Activating environment
^^^^^^^^^^^^^^^^^^^^^^

Following installation, you must activate the local DIALS environment:

.. code-block::

  source /path/to/installation/directory/dials-dev/dials_env.sh

Check you are in the correct environment and have the necessary tools available with:

.. code-block::

  which dlstbx.wrap

and check the output is pointing to your local DIALS installation.

Getting started with Zocalo
---------------------------

Start learning `at this document <tutorials/tutorial_0.rst>`_.
