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

import math
import re
import logging

from demodocusfw.build_data import BuildData
from demodocusfw.utils import color_contrast_ratio

logger = logging.getLogger('crawler.webbuilddata')


class WebBuildData(BuildData):
    """Class that captures data about performing an action on an element for the
    build user. This data is later consumed by UserModels that crawl the graph
    to estimate if they could perform that action on that element (at the given
    state), without actually interacting with page.

    The base BuildData class defines the initializer and the only function that
    is meant to be called from other parts of the framework:
    BuildData::get_data(...). This step iterates through all of the implemented
    methods that capture data and lazy loads their value into the
    WebBuildData::data instance attribute.

    Instance attributes:
        methods: list of class methods that are implemented to generate and save
                 build data. Must be created first during the __init__ call,
                 otherwise other instance attributes will be included in this
                 list.
        data: dict of fields saved that describe the page according to the build
              user. This dict is filled with the lazy loading functions that are
              called in get_data().

    """

    def _set_colors(self, web_access, action, element):
        """Set colors. This function is only called from self.fore_color and
        self.back_color.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        """

        el_color, el_alpha, bkgd_color = web_access.get_el_colors(element)
        self.data["fore_color"] = el_color + [el_alpha]
        self.data["back_color"] = bkgd_color + [1.0]

    def fore_color(self, web_access, action, element):
        """Get foreground color for the element. The value saved should be a
        list containing [r,g,b,a]

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            fore_color: list with values [r,g,b,a]

        """

        if "fore_color" not in self.data:
            self._set_colors(web_access, action, element)

        return self.data["fore_color"]

    def back_color(self, web_access, action, element):
        """Get background color for the element. The value saved should be a
        list containing [r,g,b,a] (a will always be 1)

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            back_color: list with values [r,g,b,a]

        """

        if "back_color" not in self.data:
            self._set_colors(web_access, action, element)

        return self.data["back_color"]

    def contrast_ratio(self, web_access, action, element):
        """Get contrast ratio between self.fore_color and self.back_color.
        Should be a value between 1 and 21.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            contrast_ratio: float between 1-21

        """

        if "contrast_ratio" not in self.data:

            fore_color = self.fore_color(web_access, action, element)
            back_color = self.back_color(web_access, action, element)

            contrast_ratio = color_contrast_ratio(fore_color, back_color)

            self.data["contrast_ratio"] = contrast_ratio

        return self.data["contrast_ratio"]

    def _set_height_width(self, web_access, action, element):
        """Set height/width for the element. This function is only called from
        self.height and self.width.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        """

        size = web_access.get_selenium_element(element).size
        self.data["height"] = size["height"]
        self.data["width"] = size["width"]

    def height(self, web_access, action, element):
        """Get height of the element (in pixels).

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            height: int greater or equal to zero

        """

        if "height" not in self.data:
            self._set_height_width(web_access, action, element)

        return self.data["height"]

    def width(self, web_access, action, element):
        """Get width of the element (in pixels).

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            width: int greater or equal to zero

        """

        if "width" not in self.data:
            self._set_height_width(web_access, action, element)

        return self.data["width"]

    def font_size(self, web_access, action, element):
        """Get font size of the element.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            font_size: float greater or equal to zero

        """

        if "font_size" not in self.data:
            font_size_str = web_access.get_selenium_element(element). \
                value_of_css_property('font-size')
            font_size = float(re.sub('[^\d.]+', '', font_size_str))
            self.data["font_size"] = font_size

        return self.data["font_size"]

    def xy_loc(self, web_access, action, element):
        """Get (x,y) pixel location of the element.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            xy_loc: dict with keys "x" and "y" with values of int

        """
        if "xy_loc" not in self.data:
            el_loc = web_access.get_el_location(element)
            self.data["xy_loc"] = {"x": el_loc["x"], "y": el_loc["y"]}

        return self.data["xy_loc"]

    def pixel_dist(self, web_access, action, element):
        """Get pixel distance from the original element focused on the state
        to the element passed in.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            pixel_dist: float >= 0

        """

        if "pixel_dist" not in self.data:
            # TODO instead of pulling the orig_focused_xpath (may not exist on
            #  page) can we save the element's loc in these calls, and then
            #  search back through the build_data of the previous edge to get it
            #  here. Get this from the WebAccess::Element._lxml
            #  x, y = (el._lxml_element.attrib["demod_top"], el._lxml_element.attrib["demod_top"])
            #  might have to populate (if have to do this, make Element.location field)
            current_xpath = web_access._current_state_data.orig_focused_xpath
            try:
                # First, try to get the element directly from selenium
                current_el = web_access._driver.find_element_by_xpath(current_xpath)
                current_loc = current_el.location
            except:
                try:
                    # Second, try to get location from the tab_dict
                    current_loc = web_access.get_state_data().tab_dict[current_xpath]["position"]
                    assert "x" in current_loc and "y" in current_loc
                except:
                    # Finally, just use 0,0
                    current_loc = {"x": 0, "y": 0}


            el_loc = self.xy_loc(web_access, action, element)

            # possible improvement: more advanced than active_el.location
            x_dist = current_loc["x"] - el_loc["x"]
            y_dist = current_loc["y"] - el_loc["y"]

            dist = math.sqrt(x_dist ** 2 + y_dist ** 2)

            self.data["pixel_dist"] = dist

        return self.data["pixel_dist"]

    def tab_dist(self, web_access, action, element):
        """Get number of tabs from the original element focused on the state
        to the element passed in.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            tab_dist: int >= 0 (-1 if element does not exist in tab order)

        """

        if "tab_dist" not in self.data:

            tab_dist = web_access.get_tab_distance_to_el(element)

            self.data["tab_dist"] = tab_dist

        return self.data["tab_dist"]

    def tag_name(self, web_access, action, element):
        """Get tag name of the element.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            tag_name: str name of the tag

        """

        if "tag_name" not in self.data:
            tag_name = web_access.get_selenium_element(element).tag_name
            self.data["tag_name"] = tag_name

        return self.data["tag_name"]

    def text(self, web_access, action, element):
        """Get human-readable text from element.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            text: str human-readable element text

        """

        if "text" not in self.data:
            text = web_access.get_selenium_element(element).text
            text = text.replace("\n", " ")
            self.data["text"] = text

        return self.data["text"]

    def tags(self, web_access, action, element):
        """Get all necessary tags for the form scoring.

        Args:
            web_access: web access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            tags: set of tags

        """

        if "tags" not in self.data:
            tags = set()
            tags.add(web_access.get_selenium_element(element).get_attribute("innerText"))
            tags.add(web_access.get_selenium_element(element).get_attribute("value"))
            tags.add(web_access.get_selenium_element(element).get_attribute("type"))
            field_id = web_access.get_selenium_element(element).get_attribute("id")
            if field_id is not None:
                labels = web_access.query_xpath('//label[@for="%s"]' % field_id)
                # If we can read the labels, add that text to our tags.
                if labels is not None:
                    for label in labels:
                        # TODO following line removed because we cannot call
                        #  self.score_perceive() here. Maybe we filter these in
                        #  the crawl step. I think we probably need a detailed
                        #  rework of forms to make this possible.
                        #if self.score_perceive(web_access, label,
                        #                       web_access._create_edge_metrics()) > 0.0:
                        t = web_access.get_selenium_element(
                            label).get_attribute("innerText")
                        if t is not None:
                            tags.add(t)

            self.data["tags"] = tags

        return self.data["tags"]
