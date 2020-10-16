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
import time

from demodocusfw.controller import MultiController
from demodocusfw.controller.multicontroller import get_screenshot

logger = logging.getLogger('web.multicontroller_reduced')


def _try_edge_update_graph(access, state, user, action, element, graph,
                           states_to_visit, delay=0, screenshot_dir=None):
    logger.debug(f"Trying {action} on {element}")
    edge_metrics = access.perform_action_on_element(user, action, element)
    # See if the new state is a stub state
    if edge_metrics.ability_score == 0.0:
        return False, None, None  # Could not complete this action.

    new_state_data = access.get_state_data()
    # Compare the state datas to see if it's changed.
    # If it's a stub state it must be a new state, so don't need to finish the check.
    if not new_state_data.stub and new_state_data == state.data:
        # The state hasn't changed significantly. Set back the original state.
        access.set_state_direct(state)
        return False, None, None

    # This state data is different than what was there before.
    # Does it match any states we have already seen?
    was_added, new_state = graph.add_state(new_state_data)

    # Add the edge to the graph.
    new_edge = graph.add_edge(state, new_state, element, action)
    new_edge.add_data_for_user(user, edge_metrics)

    if was_added:
        logger.info(f"from {state.id} to {new_state.id} via {action} on {element} (NEW STATE)")
        # We have not yet seen this state.
        # Add the state to the graph
        get_screenshot(screenshot_dir, access, new_state.id)
        # Do not (re)visit stub states
        if not new_state_data.stub:
            # Only visit this state if there is new content.
            if len(new_state.data.elements_to_explore) > 0:
                logger.info(f"Adding state {new_state.id} to states_to_visit.")
                states_to_visit.append(new_state)
                # Generate tab order for this new state
                tab_dict, tab_els_by_index, orig_focused_xpath = access.generate_tab_order(element.xpath)
                new_state.data.tab_dict = tab_dict
                new_state.data.tab_els_by_index = tab_els_by_index
                new_state.data.orig_focused_xpath = orig_focused_xpath
            else:
                # If no new content was found, let's copy the tab data from the old state.
                new_state.data.tab_dict = state.data.tab_dict
                new_state.data.tab_els_by_index = state.data.tab_els_by_index
                new_state.data.orig_focused_xpath = state.data.orig_focused_xpath

        # Remember how this user got here.
        new_state.set_user_path(user, state.get_user_path(user) + [new_edge])
        time.sleep(delay)
    else:
        logger.info(f"from {state.id} to {new_state.id} via {action} on {element}")
        access.set_state_direct(new_state)

    return was_added, new_state, new_edge


def build_reduced(entry_point, user, graph, access, state=None, delay=0,
                  screenshot_dir=None):
    """Examines one state, returning a list of possible states user can reach.

    Args:
        entry_point: An identifier used to specify a specific state.
        user: user (instance of UserModel) or user name as string.
        graph: graph instance that is being built.
        access: Access to the user interface for retrieving actionable elements. Defaulted to None.
        state: The starting state. Defaulted to None. This allows the load_string to be used.
        delay: Specify how long process should sleep for. Defaulted to None.
        screenshot_dir: Directory to add screenshots to. Defaulted to None.

    Returns:
        A list of possible states user can reach from a specific state."""

    states_found = []

    # state is only None at beginning of entire build
    if state is None:  # Nothing crawled yet.
        if not access.load(entry_point):
            logger.error("Failed to load entry point.")
            return states_found
        was_added, state = graph.add_state(access.get_state_data())
        # Hacky: Set the state back into the access.
        access.set_state_direct(state)
        # This user can access the start state.
        state.set_user_path(user, [])
        if was_added:
            get_screenshot(screenshot_dir, access, state.id)

            # Generate the tab order for the state
            tab_dict, tab_els_by_index, orig_focused_xpath = access.generate_tab_order()
            state.data.tab_dict = tab_dict
            state.data.tab_els_by_index = tab_els_by_index
            state.data.orig_focused_xpath = orig_focused_xpath
    else:
        access.set_state(state)

    logger.info("-- Exploring state {} --".format(state.id))

    # Okay, now we should be in the desired state. Let's start searching.
    # Question: Would we ever want the actions returned by get_actions to depend on the current state?
    actions = sorted(access.get_actions())
    for action in actions:
        logger.debug("Trying action " + str(action))
        els = sorted(action.get_elements(access) & access.get_elements_to_explore())
        for el in els:
            is_new_state, found_state, new_edge = \
                _try_edge_update_graph(access, state, user, action, el, graph,
                                       states_found, delay, screenshot_dir)

            did_change_state = new_edge is not None
            # Performing action on element changes some set of elements: AE => X
            # X is identified in dom_manipulations::mark_reachable. Store X in the state data.
            if found_state is not None and not found_state.stub:
                states_found_in_order = [state]
                if action.repeatable:
                    # Is the action repeatable? For example, if we clicked on a button and advanced
                    #   an image carousel, can we do the same thing again?
                    # Keep performing AE until we stop generating novel states, or we reach some max.
                    # When we explore these new states, *only* explore the elements_to_explore X.
                    states_found_this_time = {state}
                    count = 0
                    while found_state is not None \
                            and found_state not in states_found_this_time \
                            and not found_state.stub \
                            and count < 10:
                        # Check to make sure the element still exists.
                        states_found_this_time.add(found_state)
                        states_found_in_order.append(found_state)
                        el = access.query_xpath(el.xpath, find_one=True)
                        if el is None:
                            break
                        # Otherwise do the same thing again.
                        count += 1
                        is_new_state, found_state, new_edge = \
                            _try_edge_update_graph(access, found_state, user,
                                                   action, el, graph,
                                                   states_found, delay,
                                                   screenshot_dir)
                # Okay, we found some states AE => X.
                # Try reversing the action to see if it takes us back the same way.
                # Example: We advanced through an image carousel by pressing left arrow key.
                #   Can we get back to the previous images by pressing right arrow key?
                reverse_action = action.get_reverse_action()
                # Pop the state we're in right now.
                current_state = states_found_in_order.pop()
                if reverse_action is not None:
                    while len(states_found_in_order) > 0:
                        # Make sure the element is still here.
                        el = access.query_xpath(el.xpath, find_one=True)
                        if el is None:
                            break
                        # Make sure we can perform the reverse action on this state.
                        edge_metrics = access.perform_action_on_element(user,
                            reverse_action, el)
                        if edge_metrics.ability_score == 0.0:
                            break
                        # Make sure the resulting state is valid.
                        if not access.is_state_valid():
                            break
                        # Make sure the state is what we're expecting (the previous state in the chain).
                        expected_state = states_found_in_order.pop()
                        new_state_data = access.get_state_data()
                        if new_state_data != expected_state.data:
                            break
                        # Add the edge to the graph.
                        new_edge = graph.add_edge(current_state,
                            expected_state, el, reverse_action)
                        new_edge.add_data_for_user(user, edge_metrics)
                        if not reverse_action.repeatable:
                            break  # If not repeatable, don't keep going.
                        current_state = expected_state

            if did_change_state:
                # We changed the state, so put the old one back.
                access.set_state(state)
    return states_found


class MultiControllerReduced(MultiController):
    """
    Class that controls multiple threads in order to run multiple crawlers to
    build multiple graphs. This Controller class should be used in conjunction
    with a WebAccess. (It requires the get_elements_to_explore() function, which is
    specific to WebAccess.)

    Note that this varies from the standard MultiController only in that it
    uses build_reduced() when adding tasks in build_graph().
    """

    def build_graph(self, user, entry_point=None):
        """Procedure for crawling a page/site. Returns a graph. Some pieces
        inspired by Mesbah et al. 2012.
        https://dl.acm.org/citation.cfm?id=2109208

        Args:
            user: user (instance of UserModel) or user name as string.
            load_string: An identifier used to specify a specific state. Defaulted to None.

        Returns:
            The built graph.
        """
        if not entry_point:
            entry_point = self.entry_point
        self.pool.add_task(build_reduced, entry_point=entry_point, user=user,
                           graph=self.graph, delay=self.delay,
                           screenshot_dir=self.screenshot_dir)
        # Complete graph building before continuing with crawl
        self.pool.wait_completion()
        return self.graph
