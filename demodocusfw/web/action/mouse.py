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

from selenium.webdriver.common.action_chains import ActionChains

from demodocusfw.action import Action
from demodocusfw.web.dom_manipulations import REACHABLE_ATT_NAME


logger = logging.getLogger('web.mouse_action')


class MouseClick(Action):
    """ This action simulates the user clicking an element. """
    _action_name = 'click'
    repeatable = True

    def get_elements(self, web_access):
        """Retrieves all of the elements that register mousedown, mouseup, or click events.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.

        Returns:
            All of the elements that support mousedown, mouseup, or click events.
            Also get all buttons.
        """
        # This action is supported by any elements with mousedown, mouseup, or click events.
        # Also try all buttons and links, since these don't always have event listeners attached directly.
        all_els = web_access.get_elements_supporting_js_event('click') | \
                  web_access.get_elements_supporting_js_event('mousedown') | \
                  web_access.get_elements_supporting_js_event('mouseup') | \
                  web_access.query_xpath(f'//button[@{REACHABLE_ATT_NAME}="true"][not(@disabled)]') | \
                  web_access.query_xpath(f'//a[@{REACHABLE_ATT_NAME}="true"][@href]')
        return all_els

    def _execute_simple(self, web_access, element):
        """Focuses an element and then performs mouse event.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            element: A particular element on this interface.

        """
        sel_el = web_access.get_selenium_element(element)
        # It appears there are certain things a Selenium click can do that a JavaScript click cannot,
        #   and vice-versa. Example: A JavaScript click cannot advance the image carousel on mitre.org.
        #   On the other hand, a Selenium click cannot expand the list items on test/list_partaccessible_1.
        # Our previous method of creating and dispatching a click JavaScript event was even less effective
        #   than either of these.
        # I have not been able to spend time researching the differences, but we should keep an eye on it.
        # Try a Selenium click first, and if that didn't do anything, try a simple JavaScript click.
        old_dom = web_access.get_state_data().dom
        sel_el.click()
        new_dom = web_access._get_dom()
        if old_dom == new_dom:
            logger.info("Selenium click did nothing, trying JavaScript click.")
            web_access.run_js("arguments[0].click()", sel_el)


class MouseOver(Action):
    """ This action simulates the user moving the mouse over an element. """
    _action_name = 'mouseover'

    def get_elements(self, web_access):
        """Retrieves elements that register a mouseover event.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.

        Returns:
            A list of the elements that register a mouseover event.
        """
        # This action is supported by any elements with mousedown, mouseup, or click events.
        all_els = web_access.get_elements_supporting_js_event('mouseover') | \
            web_access.query_xpath(f'//a[@{REACHABLE_ATT_NAME}="true"][@href]')
            
        return all_els

    def get_reverse_action(self):
        return MouseOut.get()

    def _execute_simple(self, web_access, element):
        """Perform the mouseover event.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            element: A particular element on this interface.

        """
        sel_el = web_access.get_selenium_element(element)
        ActionChains(web_access._driver).move_to_element(sel_el).perform()


class MouseOut(Action):
    """ This action simulates the user moving the mouse off of an element. """
    _action_name = 'mouseout'

    def get_elements(self, web_access):
        """Retrieves elements that register a mouseout event.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.

        Returns:
            A list of the elements that register a mouseout event.
        """
        # MouseOut returns NO elements. It should not be run on its own, only as a reverse to MouseOver.
        return set()

    def _execute_simple(self, web_access, element):
        """Perform the action of moving the mouse off of an element.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            element: A particular element on this interface.

        """
        # Move off the element to the upper left corner.
        """ TODO: It is not impossible that there would be some element at 0,0 that we might accidentally trigger
        by moving there. Therefore, we should think about the following strategy:
        1. Get all elements with mouseover events.
        2. Find some point not in any of those elements.
        3. Go to that point.
        """
        ac = ActionChains(web_access._driver)
        ac.w3c_actions.pointer_action.move_to_location(0, 0)
        ac.perform()
