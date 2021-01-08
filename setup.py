#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Software License Agreement (Apache 2.0)

Copyright (c) 2020, The MITRE Corporation.
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This project was developed by The MITRE Corporation.
If this code is used in a deployment or embedded within another project,
it is requested that you send an email to opensource@mitre.org in order to
let us know where this software is being used.
"""


# this setup.py was created from this template below. See it for more features.
#   https://github.com/kennethreitz/setup.py/blob/master/setup.py

import io
import os
#from shutil import rmtree

from setuptools import find_packages, setup

# Package meta-data.
NAME = 'demodocusfw'
DESCRIPTION = 'demodocusfw generates a full state graph for a web site'
URL = 'https://github.com/mitre/demodocus.git'
EMAIL = 'tbostic@mitre.org'
AUTHOR = 'Trevor Bostic'
REQUIRES_PYTHON = '>=3.8.0'
VERSION = '0.1.0'

here = os.path.abspath(os.path.dirname(__file__))

# loading required packages from 'requirements.txt'
with open(os.path.join(here, 'requirements.txt')) as f:
    required = f.read().splitlines()

# What packages are required for this module to be executed?
REQUIRED = required

# What packages are optional?
EXTRAS = {
    # 'fancy feature': ['django'],
}

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
        long_description = '\n' + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Where the magic happens:
setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type='text/markdown',
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    #package_dir={'demodocusfw': 'demodocusfw'},
    packages=find_packages(),
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
)