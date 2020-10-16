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
import os
from threading import Lock

from .edge import Edge
from .state import State

logger = logging.getLogger('crawler.graph')


class Graph:
    """A set of states connected through a series of edges. The graph represents the feasible
    states that are reachable from a start state.

    """
    def __init__(self, reset_state_inc=True):
        self.lock = Lock()
        self.states = set()
        self.edges = defaultdict(set)  # Mapping of states to outgoing edges
        self.start_state = None
        if reset_state_inc:
            State.reset_inc()

    def __contains__(self, other):
        """TODO: Does it make sense to handle this for multiple types?"""
        if type(other) == str:
            # It's a dom str
            for state in self.get_states():
                if state.data == other.data:
                    return True
        elif type(other) == State:
            for state in self.get_states():
                if state == other:
                    return True
        elif type(other) == Edge:
            for edge in self.get_edges():
                if edge == other:
                    return True
        return False

    def add_state(self, state_data):
        """ Creates a state and adds it to the graph.
        Verifies whether the state is new, returns tuple containing whether state was
        added anew and old/new state.
        Whatever structure comes out of access.get_state_data is exactly what should be passed in here.

        Args:
            state_data: A StateData object describing the state of the interface.

        Returns:
            A tuple containing True if the state was added (didn't exist previously) and the resulting state
            in the graph.
        """
        with self.lock:
            state = self.find_state_by_data(state_data)
            if not state:
                state = State(state_data)
                logger.debug("Adding new state {}".format(state.id))
                self.states.add(state)
                # If this is the first state, assume it is the start state.
                if self.start_state is None:
                    logger.debug('Assigned start state: {}'.format(state))
                    self.start_state = state
                was_added = True
            else:
                logger.debug("Found existing state {}".format(state))
                was_added = False
            return (was_added, state)

    def find_state_by_id(self, state_id):
        """Locate a specific state in the graph by the id.

        Args:
            state_id: An attribute of the State class that identifies the specific State.

        Returns:
            The specific state with id state_id if it is in the graph, None if the id does not exist
            in the graph.
        """
        for state in self.get_states():
            if state.id == state_id:
                return state
        return None

    def find_state_by_data(self, state_data):
        """Locate the existing state that matches the data.

        Args:
            state_data: A StateData object describing the state of the interface.

        Returns:
            The existing state, None if no state matches the data.
        """
        for state in self.get_states():
            if state.data == state_data:
                return state
        return None

    def add_edge(self, s1, s2, element, action):
        """ Creates an edge from s1 to s2

        Args:
            s1: The initial state.
            s2: The resulting state.
            element: The element acted upon.
            action: The action performed on element that transitions s1 to s2.


        Returns:
            The edge just created.
        """
        with self.lock:
            edge = Edge(s1, s2, element, action)
            logger.debug('Adding new edge ' + str(edge))
            # self.edges[s1.id].add(edge)
            e = self.edges[s1.id]
            e.add(edge)
            return edge

    def get_edges_for_state(self, state, user=None, sort_by_id=True):
        """Retrieves outgoing edges for a given state that is accessible by a certain type
        of user.

        Args:
            state: The given State object.
            user: user (instance of UserModel) or user name as string. Defaulted to None.
            sort_by_id: Boolean indicating a sort by id. Defaulted to True.

        Returns:
            A list of outgoing edges. Defaulted to a list, sorted by state id, for any user.

        """
        edges = self.edges[state.id]
        if sort_by_id:
            edges = sorted(edges, key=lambda e: (e.state1.id, e.state2.id))
        if user:
            return [e for e in edges if e.supports_user(user)]
        return edges

    def get_edge_between_states(self, from_state, to_state):
        """Retrieves the first edge that goes from state1 to state2.
        This is useful if you just want to quickly crawl from state1 to state2."""
        for e in self.edges[from_state.id]:
            if e.state2 == to_state:
                return e
        return None

    def get_states(self):
        """Returns the states that are in this graph.

        Returns:
            A set of the states present in the graph.
        """
        return self.states

    def get_edges(self):
        """Returns all of the edges in the graph.

        Returns:
            A combined list of all the outgoing edges from any of the states present in the graph.

        """
        return [e for s in self.states for e in self.get_edges_for_state(s)]

    def to_gml(self, build_user, filename='state_graph.gml'):
        """Outputs the graph to a file in the graph modelling
        language (gml) format.

        Args:
            filename: A string representing the file name to which the graph will be saved.
            build_user: The type of user that built the graph

        Returns:
            True on success.
        """

        abspath = os.path.abspath(filename)
        name, ext = os.path.splitext(abspath)

        assert ext == '.gml', 'filename needs to end in ".gml"'

        all_user_names = self.start_state.get_user_names()

        with open(abspath, 'w') as f:
            f.write('graph\n')
            f.write('[\n')
            f.write('    directed 1\n')
            f.write('    multigraph 1\n')
            f.write('    buildUser "{}"\n'.format(build_user.get_name()))
            for state in self.states:
                f.write('    node [\n')
                f.write('        id ' + str(state.id) + '\n')
                f.write('        label ' + str(state.id) + '\n')
                f.write('        stub "' + str(state.stub) + '"\n')
                f.write('        users "{}"\n'.format(','.join(sorted([user_name for user_name in state.get_user_names()]))))
                f.write('        paths "' + ','.join(
                        [user_name + ": " + state.get_user_path_string(user_name) for user_name in state.get_user_names()]
                    ) + '"\n')
                for current_user_name in all_user_names:
                    f.write('        {} "'.format(current_user_name) + str(state.supports_user(current_user_name)) + '"\n')
                f.write('    ]\n')

            for edge_set in self.edges.values():
                for edge in edge_set:
                    f.write('    edge [\n')
                    f.write('        source ' + str(edge.state1.id) + '\n')
                    f.write('        target ' + str(edge.state2.id) + '\n')
                    f.write('        element "' + str(edge.element) + '"\n')
                    f.write('        action "' + str(edge.action) + '"\n')
                    f.write('        users "' + ','.join(edge.get_user_names()) + '"\n')
                    # Write build_data
                    build_data = edge.user_metrics[build_user.get_name()].build_data
                    for k, v in build_data.data.items():
                        clean_k, clean_v = Graph._clean_kv(k, v)
                        f.write(f'        {clean_k} {clean_v}\n')
                    # Write user-specific data
                    for current_user_name in all_user_names:
                        edge_data = edge.get_user_data(current_user_name)
                        for k, v in edge_data.items():
                            clean_k, clean_v = Graph._clean_kv(k, v)
                            f.write(f'        {clean_k} {clean_v}\n')
                    f.write('    ]\n')
            f.write(']')

        logger.info('Graph successfully saved to: ' + abspath)
        return True

    def path(self, s1, s2, user):
        """ Returns a list of edges that <user> can follow to get from <s1> to <s2>
        Should return the shortest path.

        Args:
            s1: The starting state.
            s2: The destination state.
            user: user (instance of UserModel) or user name as string

        Returns:
            The shortest path from s1 to s2. None if no path exists between the two states.
        """

        # First of all, note that all states store the shortest path from state0 to them for each user.
        # So if s1 = state0, we can just return that.
        if s1 == self.start_state:
            return s2.user_paths[user.get_name()] if user.get_name() in s2.user_paths else None

        visited_states = set()
        paths = []
        new_paths = []
        feasible_paths = []

        logger.debug('Acquiring lock for path()')
        with self.lock:
            # Base case
            if s1 == s2:
                logger.debug('Release (Same state)')
                return []

            # Consider only edges that this user can traverse
            edges_to_visit = deque(self.get_edges_for_state(s1, user=user))

            while len(edges_to_visit) > 0:
                edge = edges_to_visit.pop()
                # No need to path to the same state twice.
                if edge.state2 in visited_states:
                    continue
                visited_states.add(edge.state2)
                if edge.supports_user(user):
                    new_paths.clear()
                    if edge.state1 == s1:
                        if edge.state2 == s2:
                            return [edge]
                        # start a new path for each edge coming out of s1
                        paths.append([edge])
                    else:
                        for path in paths:
                            if path[-1].state2 == edge.state1:
                                # any paths adjoining this edge should be extended
                                new_paths.append(path + [edge])
                                if edge.state2 == s2:
                                    # We reached destination, path is feasible
                                    logger.debug('Release (path)')
                                    # print('Found path:')
                                    # for e in new_paths[-1]:
                                    #     print(' -> {}'.format(e))
                                    return new_paths[-1]
                        paths += new_paths

                    for s2_edge in self.get_edges_for_state(edge.state2, user=user):
                        if s2_edge.state2 not in visited_states:
                            edges_to_visit.appendleft(s2_edge)
        # No feasible path found
        logger.debug('Release (None)')
        return None

    @staticmethod
    def _clean_kv(k, v):
        """Formatting key,value pairs as strings to save to gml. Replaces double
        quotes with single quotes and wraps in double quotes if the value is not
        a number (int or float)."""
        clean_k = k.replace('"', "'")
        clean_v = str(v).replace('"', "'")
        # wrapping non-numerics in quotes
        if not Graph._is_number(clean_v):
            clean_v = f'"{clean_v}"'
        elif "e" in clean_v:
            # Converting scientific notation to decimal in output
            tmp_v = float(clean_v)
            decimal_places = int(clean_v.split("e-")[1])
            clean_v = f'{tmp_v:.{decimal_places}f}'

        # Removing any ascii characters if they are present
        clean_v = clean_v.encode('ascii', errors='ignore').decode()

        return clean_k, clean_v

    @staticmethod
    def _is_number(value):
        """Using this solution: https://stackoverflow.com/q/354038"""
        try:
            float(value)
            return True
        except ValueError:
            return False
