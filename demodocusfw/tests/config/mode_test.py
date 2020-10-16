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

from demodocusfw.config.mode_accessibility import *
from demodocusfw.utils import DemodocusTemporaryDirectory


# Note: this is a reminder we're using temp dirs in crawl tests, this value
# will be overwritten by the command line.
OUTPUT_DIR = DemodocusTemporaryDirectory()

SCREENSHOTS = False

HEADLESS = True

REDUCED_CRAWL = False

# To check for changing and delayed content. We load the page multiple times and
#   wait at least THRESHOLD and at most TIMEOUT seconds to see if any content is changing.
# For testing, make these small so as to not inflate our ci time.
PAGE_CHANGE_NUM_LOADS = 1  # Load the page this many times to see if any content changes.
PAGE_CHANGE_THRESHOLD = 1  # Wait at least this long to see if any content changes.
PAGE_CHANGE_TIMEOUT = 2  # Don't wait any longer than this.
