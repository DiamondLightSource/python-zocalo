#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    description="{{cookiecutter.project_slug}}",
    install_requires=["zocalo"],
    license="BSD license",
    include_package_data=True,
    keywords="zocalo mimas",
    name="{{cookiecutter.project_slug}}",
    packages=find_packages(exclude=("tests",)),
    python_requires=">=3.7",
    setup_requires=[],
    version="0.1.0",
    zip_safe=False,
)
