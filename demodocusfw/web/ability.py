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
All UserAbilities must inherit from UserAbility and may override three scoring
functions for determining a user's ability to interact with a website:

score_perceive: Given an element, returns a 0-1 score indicating how aware this
user would be of this element and its function (zero if the user cannot detect
this element). Components that simulate low-vision and blindness should override
this.

score_navigate: Given an element, returns a 0-1 score indicating how easy it
would be for this user to navigate to this element (zero if the user cannot get
to this element). Components that define how a user can get around a page should
override this.

score_act: Given an element and a _Simple Action_, returns a 0-1 score
estimating how much effort it would take for this user to perform this action on
this element (zero if the user cannot perform this action on this element).
Components that limit a user's actions should override this. Currently,
score_act always returns 1.0 if action is in UserAbility::actions, otherwise
0.0.

In addition, a UserAbility may override the following functions:

describe: Given an element, builds a set of strings based on what this user can
perceive about the element. Components that limit what a user can see or
understand should override this.

"""

from demodocusfw.ability import UserAbility
from demodocusfw.web.action import mouse_actions, keyboard_actions


class OmniAbility(UserAbility):
    """This component represents the ability to do anything possible to an interface"""

    """
    Let's make a really simple OmniAbility that does everything easily.
    This will be used for generating the full graph of the site.
    It is not just a conglomeration of all other abilities, which are confined by
    human limitations. Rather it is able to see and do everything quickly in order to build the graph.
    """
    actions = mouse_actions | keyboard_actions

    # Can perceive anything easily.
    def score_perceive(self, web_access, el, edge_metrics):
        """Returns a score of how well an element can be perceived.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            el: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            Returns 1.0 because the OmniAbility can perceive anything.

        """
        return 1.0

    # The Omni can see everything about an element, including invisible attributes.
    def describe(self, web_access, el):
        """Completely describes an element.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            el: A particular element on this interface.

        Returns:
            A list of the innerText, value, type, name, id, and labels if any, of an element.
        """
        tags = set()
        tags.add(web_access.get_selenium_element(el).get_attribute("innerText"))
        tags.add(web_access.get_selenium_element(el).get_attribute("value"))
        tags.add(web_access.get_selenium_element(el).get_attribute("type"))
        tags.add(web_access.get_selenium_element(el).get_attribute("name"))
        tags.add(web_access.get_selenium_element(el).get_attribute("id"))
        labels = web_access.get_selenium_element(el).get_attribute("labels")
        if labels is not None:
            for label in labels:
                if self.score_perceive(web_access, label, web_access._create_edge_metrics()) > 0.0:
                    tags.add(web_access.get_selenium_element(label).get_attribute("innerText"))
        return tags

    # Can get anywhere on the page easily.
    def score_navigate(self, web_access, el, edge_metrics):
        """Returns a score of how well an element can be navigated to.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            el: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            Returns 1.0 because the OmniAbility can navigate to any element.
        """
        return 1.0

    # Can do all actions easily.
    def score_act(self, web_access, el, action, edge_metrics, toll=0.1):
        """Return a score of how well an element can be acted on.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            el: A particular element on this interface.
            action: The action to be performed on an element.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.
            toll: amount to take away from the act score. Actions take some toll on a user.

        Returns:
            Returns 1.0 because the OmniAbility can act on any element.
        """
        return 1.0
