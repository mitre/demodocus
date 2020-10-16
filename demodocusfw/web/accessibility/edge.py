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

from demodocusfw.graph import EdgeMetrics

logger = logging.getLogger('accessibility.edgemetrics')


# --
# Defining what the states are in this interface
#
class AccessibilityEdgeMetrics(EdgeMetrics):
    """ Stores metrics about traversing from one state to another.

    Added a new field to track navigation distance (self.nav_dist) and overrided
    get_output_fields() to output this new field
    """

    def __init__(self):
        super().__init__()
        self._nav_dist = None
        self._contrast_ratio = None
        self._size = None

    @property
    def nav_dist(self):
        return self._nav_dist

    @nav_dist.setter
    def nav_dist(self, nav_dist):
        if self._nav_dist is None or nav_dist < self._nav_dist:
            self._nav_dist = nav_dist

    @property
    def contrast_ratio(self):
        return self._contrast_ratio

    @contrast_ratio.setter
    def contrast_ratio(self, contrast_ratio):
        if not isinstance(contrast_ratio, float):
            logger.warning(f"Trying to set edge_metrics.contrast_ratio with "
                           f"a non-float type: {type(contrast_ratio)} and "
                           f"value: {contrast_ratio}")
        self._contrast_ratio = contrast_ratio

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        if not all([isinstance(i, int) for i in size]):
            logger.warning(f"Trying to set edge_metrics.size with non-integer "
                           f"type: {type(size)} and value: {size}")
        self._size = size

    def get_output_fields(self):
        """Additional fields to output to the gml file.

        Returns:
            output_dict: dictionary of fields to print to the gml file
        """
        output_dict = super().get_output_fields()
        output_dict["nav_dist"] = self.nav_dist
        output_dict["contrast_ratio"] = self.contrast_ratio
        output_dict["size"] = self.size

        return output_dict
