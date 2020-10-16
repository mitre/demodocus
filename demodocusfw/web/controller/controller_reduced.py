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

from collections import defaultdict, deque
import logging
import time

from demodocusfw.graph import Graph
from demodocusfw.controller import Controller

logger = logging.getLogger('web.controller_reduced')


class ControllerReduced(Controller):
    """
    Class that handles crawling through the states of the interface
    and building the graph.  This Controller class should be used
    in conjunction with a WebAccess.  (It requires the get_elements_to_explore()
    function, which is specific to WebAccess.)
    """

    def build_graph(self, user):
        """
        Procedure for crawling a page/site. Returns a graph.
        Some pieces inspired by Mesbah et al. 2012.
        https://dl.acm.org/citation.cfm?id=2109208

        Args:
            user: UserModel that represents a type of user
        Returns:
            graph.Graph representing the built graph for a given UserModel
        """

        graph = Graph()
        self.graph = graph

        # Create an initial state and add it to the graph.
        was_added, start_state = graph.add_state(self.access.get_state_data())
        self.get_screenshot(start_state.id)

        # Generate tab order for the start_state
        tab_dict, tab_els_by_index, orig_focused_xpath = self.access.generate_tab_order()
        start_state.data.tab_dict = tab_dict
        start_state.data.tab_els_by_index = tab_els_by_index
        start_state.data.orig_focused_xpath = orig_focused_xpath

        # This user can access the start state.
        start_state.set_user_path(user, [])

        states_to_visit = deque([start_state])

        # Question: Would we ever want the actions returned by
        # get_actions to depend on the current state?
        actions = sorted(self.access.get_actions())
        els_to_actions = defaultdict(list)

        current_state = start_state
        while len(states_to_visit) > 0:

            state = states_to_visit.pop()

            logger.info("-- Exploring state {} --".format(state.id))
            self._go_to_state_if_needed(current_state, state, graph)
            current_state = state

            # Now let's start searching.
            els_to_actions.clear()
            for action in actions:
                els = action.get_elements(self.access)
                els &= self.access.get_elements_to_explore()
                for el in els:
                    logger.debug(f"...Adding action {action} for element {el}")
                    els_to_actions[el].append(action)

            for el in sorted(els_to_actions.keys()):
                base_el = el
                for action in els_to_actions[el]:
                    # It's possible that el has changed due to the repeat and reverse logic below.
                    # Make sure to set it back.
                    el = base_el
                    self._go_to_state_if_needed(current_state, state, graph)

                    sel_el = self.access.get_selenium_element(el)
                    if sel_el is None:
                        break

                    logger.debug(f"Trying action {action} for element {el}")
                    is_new_state, current_state, new_edge = \
                        self._try_edge_update_graph(state, user, action, el, graph, states_to_visit)

                    # Performing action on element changes some set of elements: AE => X
                    # X is identified in dom_manipulations::mark_reachable. Store X as StateData::elements_to_explore.
                    if new_edge is not None and not current_state.stub:
                        states_found_in_order = [state, current_state]
                        if action.repeatable:
                            # Is the action repeatable? For example, if we clicked on a button and advanced
                            #   an image carousel, can we do the same thing again?
                            # Keep performing AE until we stop generating novel states, or we reach some max.
                            # When we explore these new states, *only* explore the elements_to_explore X.
                            states_found_this_time = {state}
                            count = 0
                            while new_edge is not None \
                                    and current_state not in states_found_this_time \
                                    and not current_state.stub \
                                    and count < 10:
                                if current_state not in states_found_in_order:
                                    states_found_in_order.append(current_state)
                                states_found_this_time.add(current_state)
                                # Check to make sure the element still exists.
                                # Grab the element again because since the page has
                                #   changed it might now be "stale".
                                el = self.access.query_xpath(el.xpath, find_one=True)
                                if el is None:
                                    break
                                sel_el = self.access.get_selenium_element(el)
                                if sel_el is None or sel_el.get_attribute("demod_reachable") == "false":
                                    break
                                # Otherwise do the same thing again.
                                logger.debug("Repeating...")
                                count += 1
                                is_new_state, current_state, new_edge = \
                                    self._try_edge_update_graph(
                                        current_state, user, action, el, graph, states_to_visit)

                        # Okay, we found some states AE => X.
                        # Try reversing the action to see if it takes us back the same way.
                        # Example: We advanced through an image carousel by pressing left arrow key.
                        #   Can we get back to the previous images by pressing right arrow key?
                        reverse_action = action.get_reverse_action()
                        # Pop the state we're in right now.
                        current_state = states_found_in_order.pop()
                        if reverse_action is not None:
                            while len(states_found_in_order) > 0:
                                logger.debug("Reversing...")
                                # Make sure the element is still here.
                                # Grab the element again because since the page has
                                #   changed it might now be "stale".
                                el = self.access.query_xpath(el.xpath, find_one=True)
                                if el is None:
                                    break
                                # Make sure we can perform the reverse action on this state.
                                edge_metrics = self.access.perform_action_on_element(user, reverse_action, el)
                                if edge_metrics.ability_score == 0.0:
                                    break
                                # Make sure the resulting state is valid.
                                if not self.access.is_state_valid():
                                    break
                                # Make sure the state is what we're expecting (the previous state in the chain).
                                expected_state = states_found_in_order.pop()
                                new_state_data = self.access.get_state_data()
                                if new_state_data != expected_state.data:
                                    break
                                # Add the edge to the graph.
                                new_edge = graph.add_edge(current_state, expected_state, el, reverse_action)
                                new_edge.add_data_for_user(user, edge_metrics)
                                logger.info(f"from {current_state.id} to {expected_state.id} via {reverse_action} on {el}")
                                current_state = expected_state
                                self.access._current_state = current_state
                                self.access._current_state_data = current_state.data
                                if not reverse_action.repeatable:
                                    # If not repeatable, don't keep going.
                                    break
        self.graph = graph
        return graph

    def _try_edge_update_graph(self, state, user, action, element, graph, states_to_visit):
        """Helper function for trying an action on a target and finding any new states and edges.
        If the state changes, both new_edge and found_state will be something.
        If the state does not change, found_state will be the same and new_edge will be None.
        If the action could not be completed, both found_state and new_edge will be None.

        Args:
            state: The state to begin exploring from.
            user: The user currently exploring.
            action: The action to perform.
            element: The target to perform the action on.
            graph: The graph for adding and finding states and edges.
            states_to_visit: A queue of states that still need to be explored. We will add any new states to this.

        Returns:
            was_added: Did this action result in a new state being added to the graph?
            found_state: The state that was found (either added or existing) by performing this action.
            new_edge: The edge that was created as a result of this action.
        """
        logger.debug(f"Trying {action} on {element}")
        edge_metrics = self.access.perform_action_on_element(user, action, element)
        if edge_metrics.error is not None:
            # There was an error. Try doing a full reset of the state.
            logger.warning(f"Resetting state and retrying {action} on {element}.")
            self.access.set_state(state)
            edge_metrics = self.access.perform_action_on_element(user, action, element)

        # See if the new state is a stub state
        if edge_metrics.ability_score == 0.0:
            # Could not complete this action.
            logger.warning(f"Failed {action} on {element}.")
            return False, None, None

        new_state_data = self.access.get_state_data()
        # Compare the state datas to see if it's changed.
        # If it's a stub state it must be a new state, so don't need to finish the check.
        if not new_state_data.stub and new_state_data == state.data:
            # The state hasn't changed significantly. Set back the original state.
            self.access.set_state_direct(state)
            return False, state, None

        # This state data is different than what was there before.
        # Does it match any states we have already seen?
        was_added, found_state = graph.add_state(new_state_data)

        # Add the edge to the graph.
        new_edge = graph.add_edge(state, found_state, element,
                                  action)
        new_edge.add_data_for_user(user, edge_metrics)

        if was_added:
            # We have not yet seen this state.
            logger.info(f"from {state.id} to {found_state.id} via {action} on {element} (NEW STATE)")
            # Add the state to the graph
            self.get_screenshot(found_state.id)
            # Do not (re)visit stub states
            if not new_state_data.stub and states_to_visit is not None:
                if len(found_state.data.elements_to_explore) > 0:
                    states_to_visit.appendleft(found_state)
                    # Generate the tab order for this new state
                    tab_dict, tab_els_by_index, orig_focused_xpath = self.access.generate_tab_order(element.xpath)
                    found_state.data.tab_dict = tab_dict
                    found_state.data.tab_els_by_index = tab_els_by_index
                    found_state.data.orig_focused_xpath = orig_focused_xpath
                else:
                    # If no new content was found, let's copy the tab data from the old state.
                    found_state.data.tab_dict = state.data.tab_dict
                    found_state.data.tab_els_by_index = state.data.tab_els_by_index
                    found_state.data.orig_focused_xpath = state.data.orig_focused_xpath

            # Remember how this user got here.
            found_state.set_user_path(user, state.get_user_path(user) + [new_edge])
            time.sleep(self.delay)
        else:
            logger.info(f"from {state.id} to {found_state.id} via {action} on {element}")
            self.access.set_state_direct(found_state)

        return was_added, found_state, new_edge
