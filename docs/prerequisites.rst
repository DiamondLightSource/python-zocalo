Prerequisites
=============

Zocalo was originally developed at Diamond Light Source, a UK-based synchrotron.
The use case was providing a clear way to run complex jobs on various computing clusters.
Therefore, development of this tool was intertwined with the use of existing software tools.

This page specifies how to set up a development environment which you can later use to test new Zocalo recipes and wrappers.

DIALS
----------------

DIALS is a collaborative project for x-ray crystallography tools, which includes the dlstbx tools.
This must be installed to enable wrapper functionality in Zocalo.
Using a local copy of DIALS is also current best practice for Zocalo development.

Installation
~~~~~~~~~~~~
Detailed installation instructions are given `here
<https://dials.github.io/installation.html>`_.

Activating environment
~~~~~~~~~~~~~~~~~~~~~~

Following installation, you must activate the local DIALS environment:

.. code-block::

  source /path/to/installation/directory/dials-dev/dials_env.sh

Check you are in the correct environment and have the necessary tools available with:

.. code-block::

  which dlstbx.wrap

and check the output is pointing to your local DIALS installation.
