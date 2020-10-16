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

import logging

from .mode_default import *
from demodocusfw.web.state import WebStateData
from demodocusfw.web.user import OmniUser as WebOmniUser
from demodocusfw.web.web_access import ChromeWebAccess
from demodocusfw.web.build_data import WebBuildData

#
# Access specification - Fill in these after you have defined your Access class and Users.
#

# Specify your Access class which overrides interfaces/access.py::Access
ACCESS_CLASS = ChromeWebAccess
# Which UserModel should be the one building the graph?
BUILD_USER = WebOmniUser
# Which BuildData should be used to generate data during the build_graph step
BUILD_DATA = WebBuildData

# Class to store data for a state on our page. Defaulted to the interface, but
# can be overwritten for a specific app_context
STATE_DATA = WebStateData

#
# Web-specific parameters
#

# Make webdriver browser instance invisible to crawler users?
#  Default True (invisible). Note that when HEADLESS == False, a browser
#  window will open for every active thread.
HEADLESS = True

# For headful or headless browser instances, set the window size for all chrome
#  windows opened.
WINDOW_SIZE = (1920, 1080)

# If REDUCED_CRAWL is true, Demodocus will perform a crawl that does not explore
#  all states exhastively but focuses on states that reveal some new content.
#  It should be faster and produce smaller, more easily understandable outputs.
REDUCED_CRAWL = True

LOG_LEVEL = logging.INFO

# To check for changing and delayed content. We load the page multiple times and
#   wait at least THRESHOLD and at most TIMEOUT seconds to see if any content is changing.
PAGE_CHANGE_NUM_LOADS = 10  # Load the page this many times to see if any content changes.
PAGE_CHANGE_THRESHOLD = 8  # Wait at least this long to see if content is still changing.
PAGE_CHANGE_TIMEOUT = 20  # Don't wait any longer than this.

# Number of allowed element revisits during tab order generation before a
#  keyboard trap is declared
NUM_REVISITS = 2
