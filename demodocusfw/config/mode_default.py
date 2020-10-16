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

"""
mode_default.py - default configuration for Demodocus

This is the baseline configuration mode for the crawler. Custom configurations
should import this module and set local variable values as needed.

See documentation for details.
"""

import datetime
import logging
from pathlib import Path

from demodocusfw.analysis import BaseAnalyzer

#
# Crawl specification - what to crawl and how.
#

# Use single- or multi-threaded controller? Default to single.
# Used by the Crawler class.
MULTI = False

# How many threads? Must be positive integer.
# Used by the MultiController class.
NUM_THREADS = 1

# Delay the crawler after finding new states? Supports demos.
# Should be non-negative number, to be passed to time.sleep().
# Default 0 (no delay), unit is seconds.
# Used by the Controller class.
DELAY = 0


#
# Access specification - Fill in these after you have defined your Access class,
#  UserModels, and Analyzer
#

# Specify your Access class which overrides interfaces/access.py::Access
# ACCESS_CLASS = MyAccessClass
# Which UserModel instance should be the one building the graph?
# BUILD_USER = MyOmniUser
# Which UserModel instances should attempt to crawl the graph built by OmniUser?
# CRAWL_USERS = [User1, User2]
# Comparator pipeline
# COMPARE_PIPELINE = [
#     # Pipeline: pair of (Comparator, CompareFlags)
#     # The CompareFlags tell us whether we can stop testing based on the match result.
#     (MyComparator1(), CompareFlag.STOP_IF_TRUE),
#     (MyComparator2(), CompareFlag.STOP_IF_FALSE),
#     (MyComparator3(), CompareFlag.STOP_IF_FALSE)
# ]

# Class to analyze crawler results. By default, it will build a report and sum
#  ability scores for nodes. Any additional data needed for the given analyzer
#  should be tracked in the config, which is passed to the analyzer. The
#  BaseAnalyzer has a self.config field that can be accessed from any instance
#  method.
ANALYZER_CLASS = BaseAnalyzer

#
# Output details - what to write and where
#

# By default, generate a crawl directory based on date/time
# Used by the Crawler class and the Controller class.
utcnow = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
OUTPUT_DIR = Path('build') / 'crawls' / utcnow

# Name of crawl log file
# Used by the Crawler class.
OUTPUT_FILE = 'crawl.log'

# Which reports should be written? 'gml', 'metrics', 'dom', 'analysis',
# 'config', or default 'all', all of the above, written as a list.
# Used by the Crawler class.
REPORTS = ['all']

# Take screenshots, one for every state? These will land in OUTPUTDIR, per crawl entry point.
# Used by the Crawler class and the Controller class.
SCREENSHOTS = True

#
# Logging
#

# Used by the Crawler class.
LOG_LEVEL = logging.WARN
LOG_TO_STDOUT = True
