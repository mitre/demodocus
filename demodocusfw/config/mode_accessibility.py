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

from .mode_web import *
from demodocusfw.comparator import StrictComparator, CompareFlag
from demodocusfw.web.accessibility.edge import AccessibilityEdgeMetrics
from demodocusfw.web.accessibility.user import VizKeyUser, VizMouseKeyUser
from demodocusfw.web.analysis import WebAccessAnalyzer
from demodocusfw.web.comparator import DOMStructureComparator, \
    TextComparator as WebTextComparator

#
# Accessibility AppContext-specific parameters
#
# Which UserModels should attempt to crawl the graph built by OmniUser?
CRAWL_USERS = [VizKeyUser, VizMouseKeyUser]

# Comparator pipelines
COMPARE_PIPELINE = [
    # Pipeline: pair of (Comparator, CompareFlags)
    # The CompareFlags tell us whether we can stop testing based on the match result.
    (StrictComparator(),          CompareFlag.STOP_IF_TRUE),
    (DOMStructureComparator(),    CompareFlag.STOP_IF_FALSE),
    (WebTextComparator(),         CompareFlag.STOP_IF_FALSE)
]

# Class to store data for a state traversal. Defaulted to the interface, but
# can be overwritten for a specific app_context
EDGE_METRICS = AccessibilityEdgeMetrics

ANALYZER_CLASS = WebAccessAnalyzer
