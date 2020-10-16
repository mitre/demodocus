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

from demodocusfw.user import PCV, NAV, ACT
from demodocusfw.controller import Controller, MultiController

logger = logging.getLogger('crawler.access')


class Access:
    """ The Access class exposes functionality for accessing the browser, executable, or other
    user interface that needs to be evaluated. It allows the rest of the program to be agnostic of
    the particular software being evaluated.

    Different kinds of interfaces: command line, web, 2D executable with no access to markup, code API, VR...

    Access-related concepts:
        Interface state
            An object describing the current visual and functional configuration of the interface.
            The particular properties of the state will vary by access type.
            For example, a web browser's state will include the page DOM and maybe any cookies.
        Interface element
            An object describing an interactable area in a state. While the particular properties of an element
            will depend on the interface, an element should include some way of identifying and locating it, whether
            that is a bounding box, an xpath, or something else; and enough info to determine if it has changed or
            disappeared.
            Any part of the interface state that can be perceived and acted upon independently of the other parts
            should be considered an element.
            For example, a web browser's elements will correspond to elements in the DOM. In a blackbox executable,
            the elements may be any buttons found by performing visual analysis on the screen.
        Action (actions.Action)
            An action that the user could perform on an element.
            Some common actions are clicking or pressing a particular key.
            See actions/base.py for more information.

    When developing a new Access, ask yourself:
    - What is a state in this interface?
    - What actions can be performed in this interface?
    - What is an element in this interface (i.e., smallest unit that is acted upon)?
    - How is one state compared to another in this interface?
    - What kinds of users should be modeled for this interface?
      - Which actions should they have access to?
      - How hard would it be for them to perceive, navigate to, and activate the various elements?

    Class attributes:
        _actions: set of all actions possible in this interface.

    Instance attributes:
        _elements: Dictionary mapping of element id's to some way of accessing the element's properties.

    See docs/interfaces.md for more information on setting up an Access class.
    """

    class Element:
        """What is an element in this interface?
        An element is the smallest unit that a user would want to interact with. """
        def __init__(self):
            """What data do we want to store about an element?
            Store whatever is needed to identify the element in reports,
            whatever is needed to locate the element in the interface,
            and whatever is needed for quickly accessing the element's properties.
            """
            pass

        def __str__(self):
            """Returns a string representation of the element."""
            return self.get_short_representation()

        def __eq__(self, other):
            """Compares this element to another element by their string representations.

            Args:
                other: Element to be compared to.

            Returns:
                True if the string representations are the same.
            """
            return str(self) == str(other)

        def __lt__(self, other):
            """Compares to see if the string representation of this element is less than the string
            representation of another element.

            Args:
                other: Element to be compared to.

            Returns:
                True if the string representation of this element is less than the string representation of
                the other element.
            """
            return str(self) < str(other)

        def __hash__(self):
            return hash(str(self))

        def get_short_representation(self):
            """Return a short human-readable string for identifying the element in reports or debugging. """
            return "Please define the Element class for your particular Access class."

        def get_full_representation(self):
            """Return a full representation of the element for detailed debugging.
            Can be the same as the short representation. """
            return "Please define the Element class for your particular Access class."

    _actions = None

    @classmethod
    def get_actions(cls):
        return cls._actions

    @classmethod
    def make_controller(cls, config):
        """Given the config returns a controller to use. This can vary by interface."""
        if config.NUM_THREADS > 1 or config.MULTI:
            return MultiController(cls, config)
        else:
            return Controller(cls, config)

    def __init__(self, config):
        """
        Args:
            config: A configuration module (see demodocusfw.config). Contains
             (at a minimum) the STATE_DATA and EDGE_METRICS classes.
        """
        self._entry_state = None
        self._current_state = None
        self._current_state_data = None
        self._elements = dict()
        self._state_data_cls = config.STATE_DATA
        self._edge_metrics_cls = config.EDGE_METRICS
        self._build_data_cls = config.BUILD_DATA
        self._build_user = config.BUILD_USER

        if self._actions is None:
            self._initialize_actions()

    def __del__(self):
        self.shutdown()

    def shutdown(self):
        """Do any cleanup when shutting down your access class. """
        pass

    @classmethod
    def _initialize_actions(cls):
        """Populate the _actions set with all actions supported by this interface.
        self._actions = set(Action1(), Action2(), etc.)
        """
        raise NotImplementedError()

    def load(self, launch_string):
        """Loads a particular page/screen for processing.

        Args:
            launch_string: An identifier that can vary by interface, such as a url/uri

        Returns:
            True if the page successfully loaded, else false.
        """
        raise NotImplementedError()

    def _create_state_data(self):
        """Creates a StateData object describing the current state of the interface.
        The particular properties of the state will vary by access type.
        For example, a web browser's state will include the page DOM and maybe any cookies.

        Returns:
            A StateData object describing the state of the interface.
        """
        raise NotImplementedError()

    def _create_edge_metrics(self):
        """Creates a EdgeMetrics object to track metrics of a user performing an
        action on an element.

        The particular metrics of the edge_metrics will vary by access type and
        app_context and will be initialized with a build_data object.

        Returns:
            A EdgeMetrics object that stores data for a user/edge.
        """
        build_data = self._build_data_cls()
        edge_metrics = self._edge_metrics_cls()
        edge_metrics.build_data = build_data

        return edge_metrics

    def get_state_data(self):
        """Returns the current state of the interface (stored in _current_state_data).
        Unlike get_state below, this reflects the true state of the interface at all times.
        It is updated whenever perform_action_on_element is called.
        This needs to be called by the Controller in order to create the State in the first place
        and add it to the graph.

        Returns:
            A StateData object describing the state of the interface.
        """
        if self._current_state_data is None:
            self._current_state_data = self._create_state_data()
        return self._current_state_data

    def set_state(self, state):
        """Sets the interface to a particular State.
        This should be overridden to actually update the interface.
        States can be created or gotten by calling Graph::add_state(state_data).
        At this point the access can alter the state if desired to make crawling easier, injecting additional code etc.

        Args:
            state: A State object with a StateData describing the state of the interface.

        Returns:
            True if the state was successfully set.
        """
        self.set_state_direct(state)

    def set_state_direct(self, state):
        """Sets the state without changing anything else.
        This can be useful if we just want to reset to a known state from the graph."""
        if self._current_state is None:
            self._entry_state = state
        self._current_state = state
        self._current_state_data = state.data

    def get_state(self):
        """Returns the state last set using set_state.
        (This may not match the actual state of the interface, which could have changed due to
        simulated user interaction since calling set_state).

        Returns:
            The State object from the graph that represents the state of the interface.
        """
        return self._current_state

    def is_state_valid(self):
        """Returns true if the current state data is okay to add to our graph."""
        return True

    def perform_action_on_element(self, user, action, element):
        """Attempts to have user perform action on element.
        This simply passes off to action.execute. It may take into account the user's ability to perceive the element,
        navigate to the element, and activate the element.

        Args:
            user: UserModel to perform the action
            action: Action to be performed
            element: Element (of type myAccess.Element) that is the target of the action.

        Returns:
            edge_metrics: contains all of the data to assess the results of
                          performing the action on the element.
        """

        edge_metrics = self._create_edge_metrics()
        result = action.execute(self, user, element, edge_metrics)
        # Update the state data.
        self._current_state_data = self._create_state_data()
        return edge_metrics

    def simulate_action_on_element(self, user, action, element, build_em):
        """Uses the edge_metrics from the build user to guess the result of the
        user performing the action on the element.

        Args:
            user: UserModel to perform the action
            action: Action to be performed
            element: Element (of type myAccess.Element) that is the target of the action.
            build_em: edge_metrics object for the build user

        Returns:
            edge_metrics: contains all of the data to assess the results of
                          simulating the action on the element.
        """

        # Initialize an edge_metrics objects with data captured by the build_em
        edge_metrics = self._create_edge_metrics()
        edge_metrics.build_data = build_em.build_data

        # Raise warning if build_data has not yet been captured
        if not edge_metrics.build_data.is_data_captured:
            logger.error(f"build_data has not been captured. Cannot accurately "
                         f"simulate performing the action on the element")

        # Generate the score for performing the action on element (but don't
        #  actually perform it)
        ability_score = user.score(PCV|NAV|ACT, self, element, edge_metrics, action)
        edge_metrics.ability_score = ability_score

        return edge_metrics

    def capture_screenshot(self, output_path):
        """Attempts to take a screenshot of the interface and store it in output_path

        Args:
            output_path: location to store the screenshot

        Returns:
            True if successful
        """
        raise NotImplementedError()

    def reset(self):
        """Resets the access before going on to a new endpoint."""
        raise NotImplementedError()

    def reset_state(self):
        """Reset variables for the current state."""
        raise NotImplementedError()
