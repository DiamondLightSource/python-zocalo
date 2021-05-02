#!/usr/bin/env python

from setuptools import setup

_rst_section = "\n--------"

with open("README.rst") as readme_file:
    readme = readme_file.read()

    # Only take text up to the first section
    if _rst_section in readme:
        readme = readme.split(_rst_section)[0]
        readme = "\n".join(readme.split("\n")[:-1])

with open("HISTORY.rst") as history_file:
    history = history_file.read()

    # Only take text from up to 6 sections
    _history_split = history.split(_rst_section)
    if len(_history_split) > 7:
        history = _rst_section.join(_history_split[:7])
        history = "\n".join(history.split("\n")[:-1])

setup(
    long_description=readme + "\n\n" + history,
)
