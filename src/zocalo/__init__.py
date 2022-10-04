"""Top-level package for Zocalo."""

from __future__ import annotations

import logging

__author__ = "Diamond Light Source - Data Analysis Group"
__email__ = "dataanalysis@diamond.ac.uk"
__version__ = "0.24.2"

logging.getLogger("zocalo").addHandler(logging.NullHandler())


class ConfigurationError(Exception):
    pass
