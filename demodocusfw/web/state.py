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

from io import StringIO
from pathlib import Path
from time import perf_counter

from lxml import etree

from demodocusfw.graph import StateData
from demodocusfw.web import utils as wutils
from demodocusfw.web.template import HtmlTemplate

times = list()


class WebStateData(StateData):
    """ In a web interface, a state is a particular dom.
    We'll also store the url for locating it.
    The StateData gets stored inside graph states as state.data.

    Questions:
        Should we store any cookie information or browser session?
        What about server-side information if we have access to the server?
    """

    state_ext = "html"

    def __init__(self, url, dom_string):
        """Constructor for a StateData object.

        Args:
            url: String representation of the url for the web page.
            dom_string: String representation of the DOM.

        """
        super().__init__()
        self.url = url
        # the dom as a string
        self.dom = dom_string
        # the time it took for this page to load (initial url only)
        self.load_time = 0
        # the dom parsed as an lxml tree (only do this if/when we need it)
        self._lxml_tree = None
        # the template tells us which content in this state is unstable/changing randomly or with time.
        self.template = None
        self.tab_dict = None  # All the tabbable elements in order.
        self.tab_els_by_index = None # Map of tab_place -> element xpath
        self.orig_focused_xpath = None
        # elements_to_explore: In this state, we should only explore the elements that changed from the
        #   previous state, unless we are doing a "full" crawl. The elements to explore are
        #   captured in the elements_to_explore, which is a set.
        #   In our implementation, stub states will not need this since they don't get crawled.
        #   This is a list of "elements". It could eventually graduate up to the base state.
        self.elements_to_explore = None

    # --
    # Overriding generic functions
    #
    def __eq__(self, other):
        # Check stub status.
        if self.stub != other.stub:
            return False
        # If different url paths then assume different content.
        if not wutils.urls_equal(self.url, other.url, path=True, query=False, fragment=False):
            return False
        # If two stub states have the same path and query string then assume they are the same.
        # This does not take into account anchors that might change page content.
        if self.stub and other.stub and wutils.urls_equal(self.url, other.url, path=True, query=True, fragment=False):
            return True

        # Neither state is a stub state, or these are stub states with the same url path but different query strings.
        # Is the dom exactly the same?
        if self.dom == other.dom:
            return True

        t1 = perf_counter()
        # Let's see if they resemble each other.
        # Compare using the templates.
        if self.template is not None and other.template is not None:
            result = self.template == other.template
        elif self.template is not None:
            result = self.template.matches(other.dom)
        elif other.template is not None:
            result = other.template.matches(self.dom)
        else:
            # If these are two stub states with the same url path but different query strings, they wouldn't have any
            #  templates. We also know that the doms are not exactly the same.
            # Create a template for the first one, and match against the dom of the second.
            other.template = HtmlTemplate(other.dom)
            return other.template.matches_html(self.dom)
        times.append(perf_counter() - t1)
        return result

    def save(self, state_id, state_output_dir):
        super().save(state_id, state_output_dir)

        # Save the template if present.
        if self.template is not None:
            template_fname = Path(state_output_dir) / f'state-template-{state_id}.{self.state_ext}'
            with open(template_fname, 'w', encoding='utf-8') as fp:
                fp.write(str(self.template))

    def get_short_representation(self):
        """Returns a short string representation of the state."""
        return self.url + ': ' + self.dom[:20]  # Just print out the first few characters of the dom

    def get_full_representation(self):
        """Return a full representation of the state that can be used for
        distinguishing one state from another. """
        return self.dom

    def get_output_representation(self):
        """Returns representation of the state to save to a file.

        Note: This is usually different from self.get_full_representation().
        The WebAccess.StateData is an unusual case when they are the same"""
        return self.dom

    def get_output_fields(self):
        """Additional fields to output to the gml file. By default, no
        additional fields are outputted, be specific app_contexts can overwrite
        this.

        Returns:
            output_dict: dictionary of fields to print to the gml file
        """

        output_dict = {"url": self.url, "tab_dict": self.tab_dict, "tab_els_by_index": self.tab_els_by_index}

        return output_dict

    # --
    # Helper functions for doms/xpaths
    #

    def _get_tree(self):
        """Returns the DOM parsed as an lxml tree."""
        if self._lxml_tree is None:
            self._lxml_tree = etree.parse(StringIO(self.dom), parser=etree.HTMLParser())
        return self._lxml_tree

    def get_elements_by_xpath(self, xpath, find_one=True):
        """Returns lxml from an xpath."""
        result = self._get_tree().xpath(xpath)
        if find_one:
            return result[0] if len(result) > 0 else None
        else:
            return result

    def get_xpath_for_lxml(self, lxml_element):
        """Returns an xpath from an lxml element."""
        return self._get_tree().get_path(lxml_element)
