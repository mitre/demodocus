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
An Action represents something the user can do to an element that might change page content.

You must define the Actions for your user interface.

To create a new Action:
1. Override Action::get_elements(web_access). This function queries the web_access however it wants and retrieves
a set of elements that this action should be run on. These elements will be passed each in turn to the
execute function.
2.
(easy) Override Action::_execute_simple(element). Performs the action on the specified element as
the specified user. Returns None.
OR
(advanced) Override Action::execute(access, user, element, edge_metrics)). Attempts to perform the action on the
specified element as the specified user, saving additional metrics in the edge_metrics object. Returns a 0-1 value
indicating whether the user would/could perform this action and, if so, how well. Zero means the user would not or
could not perform this action on this element. The execute function should call the UserModel's scoring functions
(see users/base.py) to decide how well the user can perceive, navigate to, and perform various actions on the
target element and any other elements that might be involved. See form.py as an example.
    Do I need to override Action::execute?
    1. Could it involve multiple steps to get to a new content state?
    2. Does it involve multiple elements?
    3. Is there more than one way to accomplish it?
"""
import time

from demodocusfw.user import PCV, NAV, ACT

# We only need one of each action so save the ones we make.
_actions = dict()


class Action:
    """An Action represents something the user can do to an element that might change page content.
    There are two kinds of Actions. Simple Actions represent a single JavaScript event
    that is performed on a single element. Complex Actions, on the other hand, can make use of
    multiple Simple Actions and involve multiple elements. All Simple Actions are implemented in simple.py.

    Attributes:
        _action_name: String name that describes the action
    """
    _action_name = "base" # Descriptive name for action

    # Can we do this action more than once?
    # Example: We can click multiple times on the same element, but we can't mouseover multiple times.
    # If repeatable is True the crawler will perform it multiple times to discover new edges and states.
    # Example: We click on a list item and it expands to reveal new content. We click on it
    #   again and the content is collapsed. We have discovered one new state and two edges.
    # Another example: We click on a left arrow and an image carousel advances. We click the same
    #   arrow again and the image carousel advances again. Eventually we return to the initial
    #   state, after having discovered several new states.
    # If an action is not repeatable, perhaps it is reversible (see get_reverse_action below).
    repeatable = False

    @classmethod
    def get(cls, *args):
        """Static method used to instantiate actions.
        Static getter for actions. Use this instead of the constructor.
        It will create a new action or return an existing one. To use it, pass
        the arguments just as you would for the constructor.

        Args:
            args: This function accepts any number of arguments and passes them along to the class's constructor.
            The number of args will vary based on the constructor of the particular derived class.

        Returns:
            An instance of the class used to call the get function.

        Examples:
            Don't use: KeyPress(KeyCodes.ESCAPE).
            Do use: KeyPress.get(KeyCodes.ESCAPE).

        """
        key = (cls,) + args
        if key not in _actions:
            _actions[key] = cls(*args)
        return _actions[key]

    def __str__(self):
        """Returns the action name of the instance

        Returns:
            The action name as a string
        """
        return self._action_name

    def __repr__(self):
        return str(self)

    def __hash__(self):
        """Creates a hash using the string to create an instance identifier.

        Returns:
            A hash of the class instance
        """
        return hash(str(self))

    def __eq__(self, other):
        """ Compares the generated hash of two instances

        Args:
            other: Hash from class instance to compare

        Returns:
            Boolean true if the hashes are equal, false otherwise
        """
        return hash(self) == hash(other)

    def __lt__(self, other):
        """Used for sorting actions using their string representations.
        At this time, the only reason this is overloaded is so we can sort tuples that include Actions
        without raising an exception (see users/base.py::UserModel::score_navigate_act).
        Maybe think about implementing a priority at some point.

        Args:
            other: Class instance to compare

        Returns:
            Boolean true if the string representation of this class is less than other, false otherwise.
        """

        return str(self) < str(other)

    def get_elements(self, access):
        """Retrieve all the elements that this action should be attempted on.

        Args:
            access: Access to the user interface for retrieving actionable elements.

        Returns:
            Set of elements that actions should be attempted on.
        """
        return set()

    def get_reverse_action(self):
        """If this action has an "opposite" action, include that here.
        The reverse action should possibly undo the effects of this action.
        Example: Mouseover has a reverse action of mouseout. If mouseover caused
        some new content to be revealed, we guess that a mouseout might
        cause that content to be hidden again. This isn't for certain,
        but it's a reasonable guess and something we want the crawler to try.

        Returns:
            An Action instance, or None if this action has no reverse counterpart.
        """
        return None

    def execute(self, access, user, element, edge_metrics):
        """ Performs this action. Don't override this. Override either
        _execute_simple or _execute_advanced.

        Args:
            access: An Access class for working with a user interface.
            user: UserModel attempting the execution.
            element: Page element to execute this action on.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            Score 0-1 indicating how able the user is to do this action, where 0 is impossible.
        """
        return self._execute_advanced(access, user, element, edge_metrics)

    def _execute_advanced(self, access, user, element, edge_metrics):
        """Performs this action.

        Args:
            access: An Access class for working with a user interface.
            user: UserModel attempting the execution.
            element: Page element to execute this action on.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            Score 0-1 indicating how able the user is to do this action, where 0 is impossible.
        """
        # Can the user see and get to the element?
        # Does the user have an ability that can do this action?
        element_score = user.score(PCV|NAV|ACT, access, element, edge_metrics,
                                   action=self)
        edge_metrics.ability_score = element_score
        if element_score == 0:
            return 0

        # Execute stuff here.
        t0 = time.time()
        self._execute_simple(access, element)
        edge_metrics.act_time = time.time() - t0

        return element_score

    def _execute_simple(self, access, element):
        """ Performs this action.

        Args:
            access: An Access class for working with a user interface.
            element: Page element to execute this action on.

        Returns:
            None.
        """
        pass
