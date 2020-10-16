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

All UserAbilities must inherit from UserAbility and may override
three scoring functions for determining a user's ability to interact
with a website:

score_perceive: Given an element, returns a 0-1 score indicating
how aware this user would be of this element and its function (zero
if the user cannot detect this element). Components that simulate
low-vision and blindness should override this.

score_navigate: Given an element, returns a 0-1 score indicating
how easy it would be for this user to navigate to this element (zero
if the user cannot get to this element). Components that define how
a user can get around a page should override this.

score_act: Given an element and a _Simple Action_, returns a 0-1
score estimating how much effort it would take for this user to
perform this action on this element (zero if the user cannot perform
this action on this element).  Components that limit a user's actions
should override this.  Currently, score_act always returns 1.0 if
action is in UserAbility::actions, otherwise 0.0.

In addition, a UserAbility may override the following functions:

describe: Given an element, builds a set of strings based on what
this user can perceive about the element.  Components that limit
what a user can see or understand should override this.
"""

import math

from demodocusfw.ability import UserAbility
from demodocusfw.web.action import mouse_actions, keyboard_actions


class MouseAbility(UserAbility):
    """ This component represents the ability to use the mouse. """
    actions = mouse_actions

    def score_navigate(self, web_access, el, edge_metrics, nav_scale=5, max_width=100):
        """
        Finds the distance to el via pixel distance and maps it to
        [0,1].  Is there ever an issue where the mouse cannot
        navigate? Using web_access.get_pixel_distance_to_el will
        take in account elements not currently on the screen

        Args:
            web_access: Web interface to interact with the browser
            el: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.
            nav_scale: numeric that scales the mapping
            max_width: numeric that caps the pixel width of an element for Fitts

        Returns:
            nav_score: fuzzy value representing difficulty of navigating to el
        """
        # get distance and width, capping width at max_width
        dist = edge_metrics.build_data.pixel_dist(web_access, None, el)
        edge_metrics.nav_dist = dist

        width = min(edge_metrics.build_data.width(web_access, None, el), max_width)

        # using Fitt's Law to compute a navigation score
        fitts = 1 + dist/width
        if fitts <= 0:
            return 0.0
        nav_score = math.log2(fitts)

        # need to convert to our [0, 1] / [hard, easy] scale, not allowing it to
        # ...be below 0.000001
        nav_score = (nav_scale - nav_score) / nav_scale
        nav_score = max(nav_score, 0.000001)

        return nav_score


class KeyboardAbility(UserAbility):
    """ This component represents the ability to use the keyboard. """
    actions = keyboard_actions

    def score_navigate(self, web_access, el, edge_metrics, nav_scale=4):
        """Finds the distance to el via tabs and maps it to [0,1].
        TODO Incorporate skiplinks rules somehow?

        Args:
            web_access: Web interface to interact with the browser
            el: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.
            nav_scale: value that scales the mapping

        Returns:
            nav_score: fuzzy value representing difficulty of navigating to el
        """
        # get the number of tabs the focused element is to el (either direction)
        tabs_away = edge_metrics.build_data.tab_dist(web_access, None, el)
        edge_metrics.nav_dist = tabs_away
        if tabs_away < 0:
            # Impossible to tab to this element
            return 0.0
        elif tabs_away == 0:
            # No tabs needed to get to this element
            return 1.0

        # transform to log scale
        nav_score = math.log2(tabs_away)

        # need to convert to our [0, 1] / [hard, easy] scale, not allowing it to
        # ...be below 0.000001
        nav_score = (nav_scale - nav_score) / nav_scale
        nav_score = max(nav_score, 0.000001)

        return nav_score


class VisionAbility(UserAbility):
    """
    This class represents a user with normal vision.
    It can serve as a base class for other vision-related components.
    """
    def score_perceive(self, web_access, el, edge_metrics):
        """Evaluate the user's ability to perceive el, based on contrast & size

        Args:
            web_access: Web interface to interact with the browser
            el: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            contrast_multiplier: perceive_score float in [0, 1]
        """

        # For a full-vision person.
        # How hard is it to perceive based on color?
        # c_multiplier is the contrast multiplier [0,1] on how hard/easy it is
        #  to see the element based on contrast. c_multiplier is the contrast
        #  ratio used by WCAG [1,21]
        c_multiplier, c_ratio = self._get_contrast_multiplier(web_access, el,
                                                              edge_metrics)
        edge_metrics.contrast_ratio = c_ratio
        if c_multiplier == 0:
            return 0.0
        # How hard is it to perceive based on size?
        #  size_multiplier is the score [0,1] on how hard/easy it is to see the
        #  element based on size. size is a 2-tuple of element (width, height).
        size_multiplier, size = self._get_size_multiplier(web_access, el,
                                                          edge_metrics)
        edge_metrics.size = size
        return size_multiplier * c_multiplier


    @staticmethod
    def _get_contrast_multiplier(web_access, el, edge_metrics,
                                 reg_text_cutoff=4.5, large_text_cutoff=3.0):
        """Returns the contrast_multiplier for a given element on a page.
        Uses AA WCAG 2 standards: https://webaim.org/articles/contrast/

        Args:
            web_access: Web interface to interact with the browser
            el: WebAccess::Element representing the element to find dist to
            reg_text_cutoff: min contrast ratio for regular-sized text
            large_text_cutoff min contrast ratio for large text

        Returns:
            contrast_multiplier: 0.0 or 1.0, representing complaince with WCAG
            contrast_ratio: contrast ratio used by WCAG
        """
        # getting contrast ratio
        contrast_ratio = edge_metrics.build_data.contrast_ratio(web_access, None, el)

        # getting font size
        font_size = edge_metrics.build_data.font_size(web_access, None, el)

        # Applying strict cutoffs for WCAG 2 AA standards
        if font_size < 18:
            if contrast_ratio >= reg_text_cutoff:
                return 1.0, contrast_ratio
            else:
                return 0.0, contrast_ratio
        else:
            if contrast_ratio >= large_text_cutoff:
                return 1.0, contrast_ratio
            else:
                return 0.0, contrast_ratio

    @staticmethod
    def _get_size_multiplier(web_access, el, edge_metrics, min_pixels=44):
        """Returns the size_multiplier for a given element on a page.
        Uses AAA WCAG 2: https://www.w3.org/WAI/WCAG21/quickref/#target-size

        Args:
            web_access: Web interface to interact with the browser
            el: WebAccess::Element representing the element to find dist to
            min_pixels: Number of pixels to an element must be in each dimension

        Returns:
            size_multiplier: 0.0 or 1.0, representing complaince with WCAG
            size_xy: tuple (x, y), representing the width, height of the el
        """
        # ignoring this check for inline tags
        # TODO are there others?
        exception_tags = ["li", "ul"]

        height = edge_metrics.build_data.height(web_access, None, el)
        width = edge_metrics.build_data.width(web_access, None, el)
        tag_name = edge_metrics.build_data.tag_name(web_access, None, el)

        if tag_name in exception_tags or (height >= min_pixels and width >= min_pixels):
            return 1.0, (width, height)
        else:
            return 0.0, (width, height)

    def describe(self, web_access, el):
        """Describes an element based on its innerText, value, type, id, and any labels if they are
        perceivable.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            el: WebAccess::Element representing the element to find dist to

        Returns:
            A list containing the innerText, value, type, id, and any perceivable labels of an element.
        """
        # Normal users can see things like text and input type as well as any labels.
        # TODO: Consider surrounding elements?
        # TODO does not consider the tags gathered by the build_data. Since this
        #  method is not called during the crawl_graph step (by
        #  access::simulate_action_on_el), it is okay to leave the call to
        #  self.score_perceive()
        tags = set()
        tags.add(web_access.get_selenium_element(el).get_attribute("innerText"))
        tags.add(web_access.get_selenium_element(el).get_attribute("value"))
        tags.add(web_access.get_selenium_element(el).get_attribute("type"))
        field_id = web_access.get_selenium_element(el).get_attribute("id")
        if field_id is not None:
            labels = web_access.query_xpath('//label[@for="%s"]' % field_id)
            # If we can read the labels, add that text to our tags.
            if labels is not None:
                for label in labels:
                    if self.score_perceive(web_access, label, web_access._create_edge_metrics()) > 0.0:
                        t = web_access.get_selenium_element(label).get_attribute("innerText")
                        if t is not None:
                            tags.add(t)
        return tags


class LowVisionAbility(VisionAbility):
    """
    This class represents a user with low or reduced vision.
    Some additional restraints are included to match WCAG AAA standards.
    """
    @staticmethod
    def _get_contrast_multiplier(web_access, el, edge_metrics,
                                 reg_text_cutoff=7.0, large_text_cutoff=4.5):
        # using VisionAbility._get_contrast_multiplier() with stricter cutoffs
        packed_c = VisionAbility._get_contrast_multiplier(web_access, el,
                                                          edge_metrics,
                                                          reg_text_cutoff,
                                                          large_text_cutoff)
        return packed_c


class SuperVisionAbility(VisionAbility):
    """
    This class represents a user with a heightened vision ability. The values
    used here are well above the WCAG standards.
    """
    @staticmethod
    def _get_contrast_multiplier(web_access, el, edge_metrics,
                                 reg_text_cutoff=2, large_text_cutoff=1.5):
        # using VisionAbility._get_contrast_multiplier() with looser cutoffs
        packed_c = VisionAbility._get_contrast_multiplier(web_access, el,
                                                          edge_metrics,
                                                          reg_text_cutoff,
                                                          large_text_cutoff)
        return packed_c

    @staticmethod
    def _get_size_multiplier(web_access, el, edge_metrics, min_pixels=1):
        # using VisionAbility._get_size_multiplier() with looser cutoffs
        packed_s = VisionAbility._get_size_multiplier(web_access, el,
                                                      edge_metrics, min_pixels)
        return packed_s


class ScreenReaderAbility(UserAbility):
    """ (Not implemented) A component that simulates a user's perception and navigation with a screen reader. """

    def score_perceive(self, web_access, el, edge_metrics):
        """Returns a score of how well the element can be perceived.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            el: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            A score between 0 and 1 representing how difficult it is to perceive an element.
        """
        # TODO: Calculate this.
        # What does Jaws read to us?
        return 1.0

    def describe(self, web_access, el):
        """Returns a description of an element by a ScreenReaderAbility.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            el: A particular element on this interface.

        Returns:
            An empty set.

        """
        # TODO: Calculate this.
        # What does Jaws tell us about the element?
        return set()

    def score_navigate(self, web_access, el, edge_metrics):
        """Returns a score of how well an element can be navigated to.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            el: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            Returns 1.0 because the ScreenReaderAbility can navigate to any element.
        """
        # TODO: Calculate this.
        # How does Jaws navigate?
        return 1.0
