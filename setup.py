#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    setup.py
    ~~~~~~~~

    no description available

    :copyright: (c) 2019 by biagio.
    :license: see LICENSE for more details.
"""

import codecs
import os
import re

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    """Taken from pypa pip setup.py:
    intentionally *not* adding an encoding option to open, See:
       https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    """
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='replus',
    version=find_version("replus", "__init__.py"),
    description="A wrapper for Python's re library for advanced regex pattern management",
    long_description=read('README.rst'),
    classifiers=[
    ],
    author='Biagio Distefano',
    author_email='biagiodistefano92@gmail.com',
    url='https://github.com/raptored01/replus',
    packages=[
        'replus'
    ],
    platforms='any',
    license='LICENSE',
    install_requires=[
    ],
    test_suite='nose.collector',
    tests_require=['nose'],
)
