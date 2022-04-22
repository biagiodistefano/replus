#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    setup.py
    ~~~~~~~~

    A library for managing regex in a template fashion

    :copyright: (c) 2022 by Biagio Distefano.
    :license: see LICENSE for more details.
"""

import codecs
import os
import re
from pathlib import Path

from setuptools import setup

here = Path(__file__).resolve().parent


def read(filepath):
    """Taken from pypa pip setup.py:
    intentionally *not* adding an encoding option to open, See:
       https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    """
    return codecs.open(here / filepath, 'r').read()


def find_version(init_path):
    version_file = read(init_path)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='replus',
    version=find_version("replus/__init__.py"),
    description="A wrapper for the regex library for advanced regex pattern management",
    long_description=read('README.rst'),
    classifiers=[
    ],
    author='Biagio Distefano',
    author_email='me@biagiodistefano.io.com',
    url='https://github.com/biagiodistefano/replus',
    packages=[
        'replus'
    ],
    platforms='any',
    license='LICENSE',
    install_requires=[
        'regex==2022.3.15'
    ],
    test_suite='nose.collector',
    tests_require=['nose'],
)
