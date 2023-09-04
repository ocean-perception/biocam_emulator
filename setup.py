#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Copyright (c) 2023, Miquel Massot
All rights reserved.
Licensed under the BSD-3-Clause License.
See LICENSE.md file in the project root for full license information.
"""

from pathlib import Path

from setuptools import find_packages, setup

GITHUB_URL = "https://github.com/miquelmassot/zeroros"


classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "License :: OSI Approved :: BSD License",
    "Programming Language :: Python :: 3",
    "Topic :: Software Development",
    "Topic :: Software Development :: Libraries",
    "Topic :: Software Development :: Libraries :: Python Modules",
]

# read the contents of README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="biocam_emulator",
    version="1.0.0",
    description="BioCam emulator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Miquel Massot",
    author_email="miquel.massot@gmail.com",
    maintainer="Miquel Massot",
    maintainer_email="miquel.massot@gmail.com",
    url=GITHUB_URL,
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=classifiers,
    entry_points={
        "console_scripts": ["biocam_emulator = biocam_emulator.emulator:main"]
    },
    package_data={"biocam_emulator": ["data/*"]},
    include_package_data=True,
    license="BSD-3-Clause",
    install_requires=[
        "numpy>=1.23.4",
        "setuptools>=59.6.0",
    ],
    project_urls={"Bug Reports": GITHUB_URL + "/issues", "Source": GITHUB_URL},
)
