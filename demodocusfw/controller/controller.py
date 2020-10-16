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

from collections import deque
import logging
from pathlib import Path
import time

from selenium.common.exceptions import TimeoutException

from demodocusfw.graph import Graph
from demodocusfw.utils import get_screenshot_dir
from demodocusfw.web.utils import serve_output_folder

logger = logging.getLogger('crawler.controller')


class Controller:
    """Class that handles crawling through the states of the interface and building the graph."""
    def __init__(self, access_class, config):
        self.delay = config.DELAY
        self.screenshot_dir = get_screenshot_dir(config)
        self.access_class = access_class
        self.config = config
        self.access = None
        self.graph = None
        self.build_user = config.BUILD_USER
        self.crawled_users = set()

        # Has to be in the controller, not the WebAccess, for multi-threading.
        # (Each thread has its own access with its own memory space.)
        self._server = serve_output_folder(config)

        self.get_access()

    def get_screenshot(self, state_id):
        """Get a screenshot from the access of the current state

        Args:
            state_id: int id of the state to get a screenshot from
        """
        if self.screenshot_dir:
            screenshot_path = Path(self.screenshot_dir) / 'state-{}.png'.format(state_id)
            # Note: webdriver wants a string, not a Path
            try:
                self.access.capture_screenshot(str(screenshot_path))
            except TimeoutException as e:
                # This item is not screenshot-able, like a pdf.
                logger.warning(f"Could not take a screenshot of state {state_id}.")
                pass

    def build_graph(self, user, start_state=None):
        """Procedure for crawling a page/site. Returns a graph.
        Some pieces inspired by Mesbah et al. 2012.
        https://dl.acm.org/citation.cfm?id=2109208

        Args:
            user: UserModel that represents a type of user
            start_state: graph.State that represents the starting state or None
        Returns:
            graph.Graph representing the built graph for a given UserModel
        """

        graph = Graph()
        self.graph = graph

        # If no start state specified, use the current state.
        if start_state is None:
            was_added, start_state = graph.add_state(self.access.get_state_data())
            if was_added:
                self.get_screenshot(start_state.id)
                # Generate tab order for the start_state
                tab_dict, tab_els_by_index, orig_focused_xpath = self.access.generate_tab_order()
                start_state.data.tab_dict = tab_dict
                start_state.data.tab_els_by_index = tab_els_by_index
                start_state.data.orig_focused_xpath = orig_focused_xpath

        # This user can access the start state.
        start_state.set_user_path(user, [])

        states_to_visit = deque([start_state])

        while len(states_to_visit) > 0:
            state = states_to_visit.pop()

            logger.info(f"-- Exploring state {state.id}")
            if not self.access.set_state(state):
                raise RuntimeError(f"Unable to set state {state.id}")

            logger.debug("...testing...")

            # Okay, now we should be in the desired state. Let's start searching.
            for action in self.access.get_actions():
                els = sorted(action.get_elements(self.access))
                for el in els:
                    logger.debug(f"Trying {action} on {el}")
                    edge_metrics = self.access.perform_action_on_element(user, action, el)
                    # See if the new state is a stub state
                    if edge_metrics.ability_score > 0.0:
                        new_state_data = self.access.get_state_data()
                        # Compare the state datas to see if it's changed.
                        if new_state_data.stub or new_state_data != state.data:
                            # This state data is different than what was there before.
                            # Does it match any states we have already seen?
                            was_added, new_state = graph.add_state(new_state_data)

                            # Add the edge to the graph.
                            new_edge = graph.add_edge(state, new_state, el, action)
                            new_edge.add_data_for_user(user, edge_metrics)

                            if was_added:
                                # We have not yet seen this state.
                                # Add the state to the graph
                                logger.info(f"from {state.id} to {new_state.id} via {action} on {el} (NEW STATE)")
                                self.get_screenshot(new_state.id)
                                # Do not (re)visit stub states
                                if not new_state_data.stub:
                                    states_to_visit.appendleft(new_state)

                                    # Generate the tab order for this new state
                                    tab_dict, tab_els_by_index, orig_focused_xpath = self.access.generate_tab_order(el.xpath)
                                    new_state.data.tab_dict = tab_dict
                                    new_state.data.tab_els_by_index = tab_els_by_index
                                    new_state.data.orig_focused_xpath = orig_focused_xpath
                                # Remember how this user got here.
                                new_state.set_user_path(user, state.get_user_path(user) + [new_edge])

                                time.sleep(self.delay)
                            else:
                                logger.info(f"from {state.id} to {new_state.id} via {action} on {el}")

                            # Now put the old dom back.
                            self.access.set_state(state)

                        # Set the access's state back to what it was before we
                        #  tried that action
                        else:
                            self.access.set_state_direct(state)
        self.graph = graph
        return graph

    def crawl_graph(self, user, graph=None, start_state=None):
        """ Given a graph of all possible states and state transitions.
        Tags all the edges and states that can be reached by this user

        Args:
            user: UserModel that represents a type of user
            graph: graph.Graph representing the already-built graph for OmniUser
            start_state: graph.State that represents the starting state or None
        """

        build_user = self.build_user.get_name()

        if user in self.crawled_users:
            return  # Already crawled with this user.

        self.crawled_users.add(user)

        if graph is None:
            graph = self.graph

        if len(graph.states) == 0:
            # Some error probably, no states available.
            # We can't crawl a graph with no states.
            logger.error("Couldn't crawl graph, no states available (probably an error with build_graph).")
            raise Exception("Couldn't crawl graph, no states available (probably an error with build_graph).")

        if start_state is None:
            start_state = graph.start_state

        # This user can access the start state.
        start_state.set_user_path(user, [])

        states_to_visit = deque([start_state])
        seen_states = {start_state}  # set of states

        while len(states_to_visit) > 0:
            state = states_to_visit.pop()

            # Just completely set the dom in the browser to this state.
            logger.info("-- Crawling state {} --".format(state.id))
            for outgoing_edge in graph.get_edges_for_state(state):

                # Simulate action based on what is captured by the build_user
                edge_metrics = self.access.simulate_action_on_element(user,
                                                                      outgoing_edge.action,
                                                                      outgoing_edge.element,
                                                                      outgoing_edge.user_metrics[build_user])

                if edge_metrics.ability_score > 0.0:
                    # The user can follow this edge.
                    outgoing_edge.add_data_for_user(user, edge_metrics)
                    current_state = outgoing_edge.state2
                    logger.info(f"found state {current_state.id}: {outgoing_edge.action} on {outgoing_edge.element}: {edge_metrics.ability_score}")
                    if current_state not in seen_states:
                        seen_states.add(current_state)
                        # Remember how this user gets to this state.
                        current_state.set_user_path(user, state.get_user_path(user) + [outgoing_edge])
                        # Add this state to the queue so we can visit it later.
                        if not current_state.stub:
                            states_to_visit.appendleft(current_state)

    def reset_graph(self):
        """Reset graph, use after one crawl ends, before another starts."""
        self.graph = Graph()
        self.crawled_users = set()

    def load(self, entry_point):
        """Load an entry point into the access object.

        Args:
            entry_point: str representing the URL, command, or other entry point to load into access

        Returns:
            True if the entry point loaded, else False.
        """
        return self.access.load(entry_point)

    def get_access(self):
        # If there is already a web access open, close it.
        if self.access is not None:
            del self.access
        self.access = self.access_class(config=self.config)

    def _go_to_state_if_needed(self, current_state, target_state, graph):
        """If the states are "equal", just reset the state data in the access.
        Otherwise do a full set.

        Args:
            current_state: The state the controller currently thinks it's in.
            target_state: The state the controller wants to be in.
            graph: The graph (not currently used, but see commented out code below)
        """
        # demod_event check to make sure the page didn't get "reloaded" by a form field submission or similar
        # where the state appears the same but may not have been correctly loaded
        if current_state is not None and current_state == target_state and 'demod_events="true"' in current_state.data.dom:
            """
            Remember that the state data holds important information about the state such as
            (for example in the web) elements_to_explore, bare_state_data, and tab_dict. Therefore,
            even if the current state and target state are evaluated to be "the same",
            we still need to set the target state which may have filled-in data members that the
            current state does not.
            """
            self.access.set_state_direct(target_state)
        else:
            self.access.set_state(target_state)

    def stop(self):
        if self.access is not None:
            self.access.shutdown()
        if self._server is not None:
            self._server.stop()

    def __del__(self):
        self.stop()
