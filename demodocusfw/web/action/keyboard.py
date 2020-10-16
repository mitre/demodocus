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

from demodocusfw.action import Action
from demodocusfw.web import KeyCodes
from demodocusfw.web.dom_manipulations import REACHABLE_ATT_NAME

logger = logging.getLogger('web.keyboard_action')


class KeyPress(Action):
    """ This action simulates the user pressing a key while an element has focus. """
    _action_name = 'key_press'
    # Some keys are not repeatable -- We shouldn't try to press them on the same element twice.
    _unrepeatable_keys = {KeyCodes.TAB, KeyCodes.ESCAPE}

    def __init__(self, key):
        self.key = key
        self.repeatable = key not in self._unrepeatable_keys

    def __str__(self):
        """Overridden to include the key represented by this class"""
        return "key_press({})".format(self.key[3])

    def get_elements(self, web_access):
        """Gets all of the elements that are registered for keypresses, keydowns, or keyup events.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.

        Returns:
            A set of elements that support keypress, keydown, or keyup events.
        """
        # This action is supported by any elements with mousedown, mouseup, or click events.
        # Also try all buttons, since these don't always have event listeners attached directly.
        els = web_access.get_elements_supporting_js_event('keypress') | \
              web_access.get_elements_supporting_js_event('keydown') | \
              web_access.get_elements_supporting_js_event('keyup') | \
              web_access.query_xpath(f'//a[@{REACHABLE_ATT_NAME}="true"][@href]')

        if self.key == KeyCodes.ENTER:
            # If ENTER, include all buttons and links.
            els |= web_access.query_xpath(f'//button[@{REACHABLE_ATT_NAME}="true"][not(@disabled)]') | \
                   web_access.query_xpath(f'//a[@{REACHABLE_ATT_NAME}="true"][@href]')

        # Filter out any elements that are not in the tab order.
        # NOTE: Question this assumption. What if some event causes focus to jump to an element that has tabIndex -1?
        return {el for el in els
                if int(web_access.get_selenium_element(el).get_attribute('tabIndex')) >= 0}

    def get_reverse_action(self):
        if self.key == KeyCodes.RIGHT_ARROW:
            return KeyPress.get(KeyCodes.LEFT_ARROW)
        if self.key == KeyCodes.LEFT_ARROW:
            return KeyPress.get(KeyCodes.RIGHT_ARROW)
        if self.key == KeyCodes.UP_ARROW:
            return KeyPress.get(KeyCodes.DOWN_ARROW)
        if self.key == KeyCodes.DOWN_ARROW:
            return KeyPress.get(KeyCodes.UP_ARROW)
        return None

    def _execute_simple(self, web_access, element):
        """Focuses an element and then perform keyboard event.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            element: A particular element on this interface.
        """
        # If this is a button or link and we're pressing enter, just click it instead.
        sel_el = web_access.get_selenium_element(element)
        sel_el.send_keys(self.key[4])


# The TabTo and TabAway actions are not currently used. Delete if not used by 3/14/2020.
class Focus(Action):
    """This action simulates a user tabbing to an element."""
    _action_name = 'focus'

    def get_elements(self, web_access):
        """Retrieves that elements that can be tabbed to.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.

        Returns:
            A set of elements that can be tabbed to.
        """
        # Do this to elements that have focus events.
        els = web_access.get_elements_supporting_js_event('focus')

        return {el for el in els
                if int(web_access.get_selenium_element(el).get_attribute('tabIndex')) >= 0}

    def get_reverse_action(self):
        return Blur.get()

    def _execute_simple(self, web_access, element):
        """Focuses an element.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            element: A particular element on this interface.
        """
        # When we input a key, the element needs to have focus.
        js = "arguments[0].focus();"
        web_access.run_js(js, web_access.get_selenium_element(element))


class Blur(Action):
    """This action simulates a user tabbing away from an element."""
    _action_name = 'blur'

    def get_elements(self, web_access):
        """Retrieves the elements that can be tabbed away from.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.

        Returns:
            A set of elements that can be tabbed away from.
        """
        # Don't return any elements. It should not be tried on its own,
        #   only as a counter to a TabTo, or as part of form-filling.
        return set()

    def _execute_simple(self, web_access, element):
        """Removes focus from an element.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            element: A particular element on this interface.
        """
        # When we input a key, the element needs to have focus.
        js = "arguments[0].blur();"
        web_access.run_js(js, web_access.get_selenium_element(element))
