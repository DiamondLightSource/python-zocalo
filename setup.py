#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = ["graypy", "stomp.py", "workflows"]
setup_requirements = []
test_requirements = ["mock", "pytest"]

needs_pytest = {"pytest", "test", "ptr"}.intersection(sys.argv)
if needs_pytest:
    setup_requirements.append("pytest-runner")

setup(
    author="Markus Gerstel",
    author_email="scientificsoftware@diamond.ac.uk",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="Infrastructure components for automated data processing at Diamond Light Source",
    entry_points={
        "console_scripts": ["zocalo.service = zocalo.service:start_service"],
        "dlstbx.wrappers": ["dummy = zocalo.wrapper:DummyWrapper"],
        "libtbx.dispatcher.script": ["zocalo.service = zocalo.service"],
        "workflows.services": [
            "Schlockmeister = zocalo.service.schlockmeister:Schlockmeister"
        ],
    },
    install_requires=requirements,
    license="BSD license",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="zocalo",
    name="zocalo",
    packages=find_packages(),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/DiamondLightSource/zocalo-python",
    version="0.5.4",
    zip_safe=False,
)
