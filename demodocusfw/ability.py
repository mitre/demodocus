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
this element). Abilities that simulate low-vision and blindness should override
this.

score_navigate: Given an element, returns a 0-1 score indicating how easy it
would be for this user to navigate to this element (zero if the user cannot get
to this element). Abilities that define how a user can get around a page should
override this.

score_act: Given an element and a _Simple Action_, returns a 0-1 score
estimating how much effort it would take for this user to perform this action on
this element (zero if the user cannot perform this action on this element).
Abilities that limit a user's actions should override this. Currently, score_act
always returns 1.0 if action is in UserAbility::actions, otherwise 0.0.

In addition, a UserAbility may override the following functions:

describe: Given an element, builds a set of strings based on what this user can
perceive about the element. Abilities that limit what a user can see or
understand should override this.

navigate: Given an element, does whatever is necessary to prepare this user to
act on that element, including scrolling, tabbing, moving the mouse, etc.
"""


class UserAbility:
    """Base class for a UserAbility.
    A UserAbility represents one way that a user can interact with or understand elements on a page.
    Multiple abilities are added to a UserModel to create that user's capabilities and behavior.

    The UserAbility has three scoring functions: perceive, navigate, act.
    Perceive score: How well can we perceive (be aware of) this element?
    Navigate score: How well can we navigate to this element?
    Act score: How well do we think we could perform the specified Simple Action on this element?
    See the functions for more details.

    A UserAbility that does not perceive things will not implement perceive (and so it will return
    zero according to the base class).
    A UserAbility that does not control inputs will not implement navigate or act.

    For instance, a MouseAbility represents a user's ability to use a mouse and is able to trigger all mouse events.
    For perceive it returns 0. For navigate it examines how far the mouse would have to move to get to
    a target element.
    """

    # The set of all Actions this ability can perform (empty for perception-focused abilities).
    actions = set()

    def prepare(self, access):
        """Performs additional actions necessary in order to interact with a page, should it be required for
        a user.

        Args:
            access: Access to the user interface for retrieving actionable elements.

        """
        # If a user with this (dis)ability would do anything to prepare for interacting with a page,
        # such as zooming in or running some plugin, do that here.
        pass

    def __lt__(self, other):
        return type(self).__name__ < type(other).__name__

    """
    The UserAbility contains five main functions:

    1. Perceive score: How well can we perceive this element?
    2. Describe: Actually perceive the element, gathering a set of descriptive tags.

    3. Navigate score: How well can we get to this element?
    4. Navigate: Actually navigate to the element.

    5. Act score: How well do we think we could perform the specified Simple Action on this element?
    (For more on Simple Actions, see actions/simple.py.)
    """

    def score_perceive(self, access, el, edge_metrics):
        """Returns a score associated with how well an element can be perceived.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            el: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            A score between 0 and 1 that represents how well an element is perceived.
        """
        # Return perceive-ability value 0-1.
        # Usual checks would be is it hidden, how small is it, how is the coloring, etc.
        # Assume the element is already on the screen.
        # Assume the element is not hidden.
        # If we can't perceive the element at all, return 0.
        # If there's no way we could miss it, return 1.
        return 0.0

    def describe(self, access, el):
        """Based on this user's abilities, attempt to build up a string describing the element.
        Users with different perceptions may end up with different pieces of information.
        This is used if we need to understand an element's purpose, ie, expecting some particular text input.
        Args:
            access: Access to the user interface for retrieving actionable elements.
            el: A particular element on this interface.

        Returns:
            A set with descriptive pieces of information.
        """
        # Given this ability, attempt to build up a set of strings describing the element.
        # Users with different perceptions may end up with different pieces of information.
        # This is used if we need to understand an element's purpose, ie, expecting some particular text input.
        # Some strategies could be looking at text, labels, surrounding elements, etc.
        return set()

    def score_navigate(self, access, el, edge_metrics):
        """Returns a score of how well the user can navigate to an element.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            el: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            A score between 0 and 1 that represent how easily the element can be navigated to.
        """
        # Measures how easy 0-1 it would be to get to this element.
        # When it is done it reverts focus, mouse position, scroll, etc. for future measurements.
        # Usually means making sure the focus is on this element, or that the mouse is over this element.
        # Assume the element is not hidden.
        # Includes scrolling/panning to make sure the element is on screen.
        # If the element was already on the screen and focused to start, we can typically return 1.
        # If there is no way to reach the element (it is hidden somehow), return 0.
        return 0.0

    def navigate(self, access, el):
        """Navigates to particular element on an interface.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            el: A particular element on this interface.
        """
        # Actually navigates to this element.
        # Call this before actually doing an action, to make sure focus, mouse position, etc. are set correctly.
        # Assume that we can perceive and reach the element.
        pass

    def score_act(self, access, el, action, edge_metrics, toll=0.1):
        """Returns a score of how easy it is easy to perform an action on a particular element.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            el: A particular element on this interface.
            action: The action to be performed on an element.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.
            toll: amount to take away from the act score. Actions take some toll on a user.

        Returns:
            A score between 0 and 1 representing how easily an action is performed on a particular element.
        """
        # Return an estimate of how hard it would be for this ability to perform this action on this element.
        # Assumes we already navigated to the target element.
        # Do not actually perform the action.
        if action not in access.get_actions():
            raise ValueError("UserAbility::score_act: %s is not an action on interface %s." %
                             (action, access))
        score = (1 - toll) if action in self.actions else 0.0
        return score
