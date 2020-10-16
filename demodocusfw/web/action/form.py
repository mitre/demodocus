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

from collections import defaultdict
import itertools
import logging

from demodocusfw.action import Action
from .keyboard import KeyPress
from .mouse import MouseClick
from demodocusfw.user import PCV, NAV, ACT
from demodocusfw.web import KeyCodes
from demodocusfw.web.dom_manipulations import REACHABLE_ATT_NAME

logger = logging.getLogger('crawler.actions.form')

"""
We are interested in whether a user can successfully fill out a form to access additional content,
resulting in the following graph:
(State_1) -FormFillAction-> (State_2).

The FormFillAction, when evaluated, should return 0-1 like any other action to indicate how hard it would be for
the user to successfully fill out the form. If the user receives an error message, the user should persist until
either (1) the form is successfully submitted or (2) all options available to that user are exhausted, returning 0.

Since not all forms use a structured <form> element, this action looks for potential submit buttons, then
moves up the DOM to discover input fields that could be associated with a particular submit button.

Maybe:
1. Leave all empty and press the button (See if multiple errors or only first.)
2. If only first, fill in each field sequentially to get an error message for each.
3. Fill all fields.
4. Correct bad fields and try again.
Use ML for detecting error messages.
"""

# Input types:
"""
checkbox
color
date
datetime
email
file
image
month
tel  Safari only
search
radio
text
password
time
url
week
"""

# This JavaScript stores whatever values we've tried in the inputs,
# so that when we come back to this state the values will be filled in.
_js_freeze_values = \
f'REACHABLE_ATT_NAME = "{REACHABLE_ATT_NAME}";' + \
"""
// How Selenium gets its "arguments" variable in JavaScript:
//  When this JavaScript is passed to the web_access.run_js function, an object is passed as the second argument
//  to that function. That object becomes arguments[0] in the JavaScript.
inputs = arguments[0];
for (i = 0; i < inputs.length; i++) {
    el = inputs[i];
    // Make sure the _reachable attribute stays last.
    reachable = el.getAttribute(REACHABLE_ATT_NAME);
    el.removeAttribute(REACHABLE_ATT_NAME);
    // Now set the value.
    if (el.getAttribute('type') == 'checkbox') {
        if (el.checked) { el.setAttribute('checked', true); }
    }
    // TODO: Handle other types of inputs.
    else if ('value' in el) {
        el.setAttribute('value', el.value);
    }
    // Put the _reachable attribute back.
    el.setAttribute(REACHABLE_ATT_NAME, reachable);
}
"""

# Actions that are expected to toggle a form element or trigger a submit button.
_activation_actions = [
    MouseClick.get(),
    KeyPress.get(KeyCodes.SPACE)
]

_enter_press = KeyPress.get(KeyCodes.ENTER)


class FormFillAction(Action):
    """ This action will attempt to successfully fill out and submit a form. """

    _action_name = 'form'

    def __init__(self):
        """ Initializes the FormFillAction
        """
        # Put the fill rules into a dictionary for fast access.
        self.fill_rules = defaultdict(lambda: defaultdict(set))
        for input_types, tags, values in form_fill_rules:
            # Convert any strings to iterables.
            if type(input_types) == str:
                input_types = (input_types,)
            if type(tags) == str:
                tags = (tags,)
            if type(values) == str:
                values = (values,)
            # Add to the dictionary.
            for input_type in input_types:
                for tag in tags:
                    for value in values:
                        self.fill_rules[input_type][tag].add(value)

    def get_elements(self, web_access):
        """ Extracts any form or other container that has input fields and buttons from the page.

        Args:
            web_access: The current web_access.

        Returns:
            The result from querying for a form and a container that has an input and button element.
        """
        # Look for a form, or for a div with an input and a button on it.
        forms = web_access.query_xpath(f'//form[@{REACHABLE_ATT_NAME}="true"]')
        # Get the lowest-level container that has both an input and a button element.
        # If there happens to be an input field without an associated button,
        #   this code might find an unrelated button and push that instead.
        divs = web_access.query_xpath(f'//input/ancestor::*[descendant::button][position()=1]')
        return forms | divs

    def _execute_advanced(self, web_access, user, element, edge_metrics):
        """ Attempts to identify, fill out, and submit the form represented by element.

        Args:
            web_access: The current web_access.
            user: The user wanting to fill out this field.
            element: Page element to execute this action on.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            0-1 value: 0 if no form could be found or the form could not be submitted,
            1 if the form required minimal effort to submit successfully.
        """

        # Save this so we can put it back after messing with the form.
        old_state = web_access.get_state()

        form = element

        edge_metrics.ability_score = 0.0

        # Find the button associated with the form.
        submit_button = web_access.query_xpath(f'.//input[@type="submit"][@{REACHABLE_ATT_NAME}="true"]|.//button[@{REACHABLE_ATT_NAME}="true"][not(@disabled)]', element=form, find_one=True)
        if submit_button is None:
            return 0.0

        # Make sure the user can access this button.
        button_score = user.score(PCV|NAV|ACT, web_access, submit_button, edge_metrics, _activation_actions)
        if button_score == 0.0:
            return 0.0

        # Get all the input fields associated with this button.
        input_fields = web_access.query_xpath(f'.//input[not(@type="submit")][@{REACHABLE_ATT_NAME}="true"]', element=form)
        if len(input_fields) == 0:
            # There are no inputs, so just click the button!
            # Example of button without inputs is the mitre.org search button.
            submit_button_sel = web_access.get_selenium_element(submit_button)
            submit_button_sel.click()
            if self._check_success(form, old_state.data.url, input_fields, web_access):
                # We submitted successfully!
                edge_metrics.ability_score = button_score
                return button_score

        input_fields_to_possible_values = dict()

        # Go through each input field. If we can access it, figure out the possible values we want to try.
        # After doing this we will try all combinations to try to submit the form successfully.
        for input_field in input_fields:
            values_to_try = self._get_values_to_try_for_input(web_access, user, input_field)
            # If it is None, there are no values we can try in this input
            # (we can't interact with it, or there was no matching rule).
            if values_to_try is not None:
                input_fields_to_possible_values[input_field] = values_to_try

        # The user has figured out which values to try in all the fields.
        # Now try them all.

        # First pass: brute force try all values.
        keys_vals = [(k, v) for k, v in input_fields_to_possible_values.items()]
        keys, vals = zip(*keys_vals)
        all_combinations = itertools.product(*vals)
        for combination in all_combinations:
            # Fill each field with the appropriate value.
            for index, input_field in enumerate(keys):
                self._set_field_value(web_access, input_field, None, combination[index])
            # We filled in all the fields, try submitting.
            submit_button_sel = web_access.get_selenium_element(submit_button)
            if submit_button_sel is None:
                # The button is hidden/unreachable. Stop executing this action.
                # This can happen if an animation covered up the button since we saved the state.
                return 0.0
            # Click the submit button!
            submit_button_sel.click()
            if self._check_success(form, old_state.data.url, input_fields, web_access):
                # We submitted successfully!
                # If the form still exists on the page, freeze the values we used into the dom
                # so that when we come back to this state the values will be filled in.
                if web_access.get_selenium_element(form) is not None:
                    web_access.run_js(_js_freeze_values, input_fields)
                    edge_metrics.ability_score = button_score
                    return button_score

        # We tried every combination of values and couldn't submit the form successfully.
        # Put back the original blank dom.
        web_access.set_state(old_state)
        return 0.0

    def _get_input_act_score(self, web_access, user, input, input_type):
        """ Return the ACT ability score for this input for this user. In other words,
        how well the user can fill out this input field (from 0-1).

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            user: The user trying to act on input.
            input: The input element.
            input_type: The type of input.

        Returns:
            Returns a score between 0 and 1 that represents the ACTing score on the input element by user.
        """

        empty_edge_metrics = web_access._create_edge_metrics()
        if input_type == 'checkbox':
            # Can use mouse or spacebar?
            return user.score(ACT, web_access, input, empty_edge_metrics, _activation_actions)
        if input_type == 'radio':
            # Can use mouse or arrow keys?
            actions = [MouseClick.get(), KeyPress.get(KeyCodes.RIGHT_ARROW)]
            return user.score(ACT, web_access, input, empty_edge_metrics, actions)

        if web_access.get_selenium_element(input).get_attribute("value") is not None:
            # This is some kind of keyboard entry field, like text or email. Can we use the keyboard?
            return user.score(ACT, web_access, input, empty_edge_metrics, _enter_press)
        else:
            # What else?
            return 0.0

    def _get_field_value(self, web_access, input_field, input_type=None):
        """ Gets the current value of an input field. Handles all types of inputs.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            input_field: The input_field element to be examined.
            input_type: A string representing the type of input it is. Defaulted to None

        Returns:
            The value of the input field.
        """
        if input_type is None:
            input_type = web_access.get_selenium_element(input_field).get_attribute("type")

        if input_type == 'checkbox':
            # If we need to change the checkbox value, try each activation task until one succeeds.
            # Assume if we can get to the element then we can change it.
            return web_access.get_selenium_element(input_field).get_attribute("checked")

        elif input_type == 'radio':
            # TODO: How should we handle radio buttons? We need a concept of the group.
            pass

        else:
            # For other fields, see if it has a value.
            my_val = web_access.get_selenium_element(input_field).get_attribute("value")
            if my_val is not None:
                # Appears to be a text value.
                return my_val

        # Not sure how to deal with this type of input.
        return None

    def _set_field_value(self, web_access, input_field, input_type, value):
        """ Sets an input field to a specified value. Handles all types of inputs.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            input_field: The input field element.
            input_type: The type of input the input field is.
            value: The the field will be set to.

        """
        if input_type is None:
            input_type = web_access.get_selenium_element(input_field).get_attribute("type")

        if input_type == 'checkbox':
            # If we need to change the checkbox value, try each activation task until one succeeds.
            # Assume if we can get to the element then we can change it.
            checked = web_access.get_selenium_element(input_field).get_attribute("checked")
            if (checked is not None) != value:
                input_field.click()  # toggle it.

        elif input_type == 'radio':
            # TODO: How should we handle radio buttons? We need a concept of the group.
            pass

        else:
            # For other fields, make sure we can type in that field, then set the value.
            my_val = web_access.get_selenium_element(input_field).get_attribute("value")
            if my_val is not None:
                # Appears to be a text value.
                if my_val != value:
                    web_access.run_js("arguments[0].value=arguments[1]", input_field, value)

    def _get_values_to_try_for_input(self, web_access, user, input_field):
        """ Given an input field, decides what values to try to fill it with.

        Args:
            web_access: Web access to the user interface for retrieving actionable elements on a web page.
            user: The user object.
            input_field: The input field element.

        Returns:
            A list of values to try to fill input_field with."""
        # Check to make sure the user is aware of this input element and can get to it.
        empty_edge_metrics = web_access._create_edge_metrics()
        pcv_nav = user.score(PCV | NAV, web_access, input_field, empty_edge_metrics)
        if pcv_nav == 0.0:
            return None

        # See if this the element has the input type and tags required by this form fill action.
        input_type = web_access.get_selenium_element(input_field).get_attribute("type")
        if input_type not in self.fill_rules and '*' not in self.fill_rules:
            return None

        input_type_rules = self.fill_rules[input_type if input_type in self.fill_rules else '*']

        # Make sure the user can act on this particular input element.
        act = self._get_input_act_score(web_access, user, input_field, input_type)
        if act == 0.0:
            return None

        # Create some tags describing this element.
        # tags is a string.
        tags = user.describe(web_access, input_field)
        # See if this action's rule matches.
        matching_tags = {key for key in input_type_rules.keys() if key in tags}
        if len(matching_tags) == 0:
            if '*' in input_type_rules:
                matching_tags = {'*'}
            else:
                return None
        return {val for matching_tag in matching_tags for val in input_type_rules[matching_tag]}

    def _check_success(self, form, prev_url, input_fields, web_access):
        """ Determines whether this form has been submitted successfully.
        How do we know that a form has submitted successfully and we
        have accessed new content?
        1. url changes (Google).
        2. input's xpath is no longer valid (the form disappeared).
        3. the form remains but all fields are cleared.
        4. the form remains but fields reset to default (not sure how to deal with this).

        Args:
            form: The element containing the input fields and submit button (usually a form element).
            prev_url: The url from when this action began.
            input_fields: All the input fields found in this form.
            web_access: The current web_access instance.

        Returns:
            True or False
        """
        success_texts = ["succe", "congrat"]
        if web_access.get_state_data().url != prev_url:
            return True  # The url changed
        # See if the word "success" appears anywhere on the form.
        f_el = web_access.get_selenium_element(form)
        if f_el is None:
            # The form no longer exists on the page, so we probably submitted it successfully.
            return True
        for t in success_texts:
            if t in f_el.get_attribute("innerText").lower():
                return True
        for input_field in input_fields:
            try:
                val = self._get_field_value(web_access, input_field)
            except:  # Stale element
                return True  # The form must have disappeared
            if val != "":
                return False  # The fields are not empty, so this must not have succeeded.
        return True  # All the fields were empty, so we must have succeeded and the fields reset.


"""
How to read these fill_rules tuples:
First item:     Rule applies to inputs with specified input type(s).
Second item:    Rule applies to inputs that have the specified "tags" (which we will construct) describing their purpose or context.
Third item:     If the rule matches, try each of these values in turn.
These represent some common inputs that users would recognize and values they would try in those inputs.
"""
form_fill_rules = (
    (("checkbox", "radio"), "*", ("true", "false")),
    ("date", "*", ("0001-01-01", "1979-01-01")),
    ("month", "*", ("0001-01", "1979-01")),
    ("week", "*", ("0001-W01", "1979-W01")),
    ("number", "*", ("-1", "0", "2", "100", "1295", "12.95")),
    ("tel", "*", "555-555-5555"),
    ("email", "*", "bob@example.com"),
    ("password", "*", ("Mbuasd$1fd", "hjfsdhskfd", "$$$orddkD21")),
    ("url", "*", "http://www.example.com/"),

    # Fields that expect numbers but allow text input
    ("text", ("date", "day"), ("01/01/1979", "1979/01/01", "Monday", "01-01-1979", "1979-01-01")),
    ("text", "time", ("10:00", "10:00AM", "10:00 AM", "10AM", "10 AM")),
    ("text", ("phone", "tel#"), ("5555555555", "555-555-5555", "(555)-555-5555", "555-5555")),
    ("text", "zip", "55555"),

    # (
    #     [
    #         {"type": "email"},
    #         {"type": "text", "tags": ["email", "e-mail"]}
    #     ], "bob@example.com"),

    # Other kinds of text
    ("text", ("email", "e-mail"), "bob@example.com"),
    ("text", ("name", "user"), ("bob smith", "smith", "bsmith", "bsmith21", "bobsmith1971")),
    ("text", "password", ("Mbuasd$1fd", "hjfsdhskfd", "$$$orddkD21")),
    ("text", "url", "http://www.example.com/"),
    (("text", "search"), "*", "testText")
)
