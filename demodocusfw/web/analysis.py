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
import os
import pathlib
import itertools
import json
import re
import logging

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
from lxml import etree
from lxml.html import html5parser

from demodocusfw.analysis import BaseAnalyzer
from demodocusfw.utils import color_contrast_ratio
from demodocusfw.web.action import keyboard_actions, mouse_actions

logger = logging.getLogger('analysis.webaccessanalyzer')


"""Customized version of BaseAnalyzer that also analyzes a graph for
accessibility violations and possible outcomes if inaccessible elements are made
accessible."""


class WebAccessAnalyzer(BaseAnalyzer):
    """Analyzer for the Web/Accessibility interface/app_context. Adds
    functionality to analyze inaccessible parts of the graph based on different
    user models. Also provides inaccessible elements, and the result of fixing
    them.
    """

    # --
    # Formatting sections. Title and guide to be printed for each section.
    #   May be overridden.
    #

    _build_sections = \
        {
            "els_states":
                {"label": "Visible Border & Tab Analysis",
                 "guide_lines":
                     [
                         ' * **valid tab order** -- all elements for a crawled state (not stub state) can be navigated to via a `TAB` key (forward and backward), and follow a logical ordering (top to bottom, left to right).',
                         ' * **visual indication of focus**  -- issues occur when an element for a crawled state (not stub state) has the same focused and unfocused style information.'
                     ]
                 }
        }

    _crawl_user_sections = \
        {
            "inacc":
                {"label": "Inaccessible Elements",
                 "guide_lines":
                     [
                         ' * any reference to a state contains a hyperlink to its corresponding `HTML` dom file'
                     ]
                 }
        }

    # --
    # Constructor/initializer. Loads in graph and sets up needed class fields.
    #   May be overridden.
    #

    def __init__(self, graph_fpath, config):
        # Initialize any parameters specific to this class
        self._dom_path = None

        # Call the super init
        super().__init__(graph_fpath, config)

        # Perform other methods specific to this class
        self._set_dom_path()

        # Variables necessary for the element map creation
        self._keyboard_actions_str = {str(act) for act in keyboard_actions}
        self._mouse_actions_str = {str(act) for act in mouse_actions}
        self._group_id = 0
        self._state_trees = dict()

    # --
    # Property (getter/setter) methods.
    #   May be overridden.
    #

    @property
    def dom_path(self):
        return self._dom_path

    def state_tree(self, state_id):
        # Load in the dom tree if it's not already loaded
        if state_id not in self._state_trees:
            path = pathlib.Path(self.output_path)
            state_fpath = path / "states" / f"state-{state_id}.html"
            tree = html5parser.parse(str(state_fpath.absolute()))
            # Drop the pesky namespaces
            tree = self._strip_ns_prefix(tree)
            self._state_trees[state_id] = tree
        else:
            tree = self._state_trees[state_id]

        return tree

    # --
    # Helper methods for initialization.
    #   May be overridden.
    #

    def _set_dom_path(self):
        # initialize the dom file path
        graph_path_obj = pathlib.Path(self.graph_fpath)
        dom_path = graph_path_obj.parent / 'dom'
        if dom_path.is_dir():
            self._dom_path = dom_path

    # --
    # Methods to perform section-specific analyses.
    #   May be overridden.
    #

    def _get_user_actions_subgraph(self, user):
        """Get the graph of nodes that is accessible for a given user's actions.

        Note: This graph is based on the actions that the user can perform. This
        would include subsets of edge that may be in an inaccessible region of
        the graph, but have the necessary actions (found by the OmniUser) to be
        accessible if they were able to be reached.

        Args:
            user: str denoting a crawl user

        Returns:
            user_actions_subgraph: networkx.graph of nodes reachable with this user's actions
        """

        user_model = self.users["crawl_users"][user]["user_model"]

        # user_model's actions
        user_actions = {str(e) for e in user_model.actions}

        # getting edges of traversable user_model's actions
        edges_with_user_action = [(u, v, k) for u, v, k, d in
                                  self.full_graph.edges(data=True, keys=True)
                                  if d['action'] in user_actions]

        # getting graph of traversable user_model's actions
        user_actions_subgraph = self.full_graph.edge_subgraph(
            edges_with_user_action).copy()

        return user_actions_subgraph

    def _get_inaccessible_graph(self, user):
        """Get the graph of nodes that is inaccessible for a given user.

        Args:
            user: str denoting a crawl user

        Returns:
            inaccessible_graph: networkx.graph of nodes the user cannot access
        """
        inaccessible_graph = self.full_graph.copy()
        user_graph = self.users["crawl_users"][user]["graph"]
        inaccessible_graph.remove_nodes_from(user_graph.nodes())

        return inaccessible_graph

    def _inaccessible_user_analysis(self, user):
        """Top-level method for the inaccessible analysis section.

        Args:
            user: str denoting a crawl user

        Returns:
            print_lines: list of lines to print to the report
        """
        print_lines = list()
        print_lines.append(f'### <a name="{user.lower()}-inacc"></a> Inaccessible Elements')

        user_graph = self.users["crawl_users"][user]["graph"]
        user_actions_graph = self._get_user_actions_subgraph(user)
        user_inaccessible_graph = self._get_inaccessible_graph(user)

        user_node_ids = list(user_graph.nodes())
        inaccessible_node_ids = list(user_inaccessible_graph.nodes())

        potential_improvements = self._find_all_accessible(user_node_ids, inaccessible_node_ids, user_actions_graph)
        _, lines = self._elements_to_fix(potential_improvements, user)

        print_lines += lines

        # update new graph G with new states included and path scores
        new_states = {k: str(sorted(v['new_states_included'])) for k, v in
                      potential_improvements.items()}
        for i in user_node_ids:
            new_states[i] = str([])
        nx.set_node_attributes(self.full_graph, new_states, f"NewStates{user[0:-4]}")

        return print_lines

    def _find_accessible_if(self, idx, user_node_ids, user_actions_graph,
                            primary_connection=True):
        """Analyzes a single state for accessible-if states for a given user

        Args:
            idx: index of a node to analyze
            user_node_ids: list of node indices that are in the user graph
            user_actions_graph: networkx graph with only action edges for user
            primary_connection: bool to denote if idx is one edge away from an already accessible state

        Returns:
            additional_user_edges: dictionary of lists "possible_edges",
            "new_states_included", "new_edges_included"
        """

        additional_user_edges = defaultdict(list)

        # get all the edges of graph G that go into node idx
        if primary_connection:
            all_edges_to_idx = list(self.full_graph.in_edges([idx], keys=True))
        else:
            all_edges_to_idx = list(user_actions_graph.in_edges([idx], keys=True))
        # get edges from all_edges_to_idx that start from a user_node
        possible_edges = [e for e in all_edges_to_idx if e[0] in user_node_ids]
        # if there are edges from the user graph nodes to the idx node
        if len(possible_edges) > 0 and user_actions_graph.has_node(idx):
            # find new edges that would be included if we add node idx to the user graph
            new_edges_included = [(u, v, k) for (u, v, k) in
                                  user_actions_graph.out_edges(idx, keys=True)
                                  if v not in user_node_ids]
            # record this in a dictionary
            new_states_included = sorted(list(set([v for (u, v, k)
                                                   in new_edges_included])))
            if primary_connection:
                additional_user_edges["possible_edges"] += possible_edges
            additional_user_edges["new_states_included"] += new_states_included
            additional_user_edges["new_edges_included"] += new_edges_included

        return additional_user_edges

    def _find_all_accessible(self, user_node_ids, inaccessible_node_ids,
                             user_actions_graph):
        """Analyzes an entire graph for accessible-if states

        Args:
            user_node_ids: list of node indices that are in the user graph
            inaccessible_node_ids: list of node indices that are not in the user graph
            user_actions_graph: networkx graph with only action edges for user

        Returns:
            potential_improvements: dictionary of lists "possible_edges", "new_states_included", "new_edges_included"
        """

        potential_improvements = dict()

        # loop through all nodes not included in the user graph
        for idx in inaccessible_node_ids:

            # initialize looping parameters for each
            primary_connection = True
            user_node_ids_copy = user_node_ids.copy()
            inaccessible_node_ids_copy = inaccessible_node_ids.copy()
            inaccessible_node_ids_copy.insert(0, inaccessible_node_ids_copy.pop(inaccessible_node_ids_copy.index(idx)))
            adtl_user_edges = defaultdict(list)

            # iterate through all the nodes not in user graph (including newly accessible nodes)
            while inaccessible_node_ids_copy:

                idx_copy = inaccessible_node_ids_copy.pop(0)

                adtl_user_edges_tmp = self._find_accessible_if(idx_copy,
                                                               user_node_ids_copy,
                                                               user_actions_graph,
                                                               primary_connection=primary_connection)
                adtl_user_edges["possible_edges"] += adtl_user_edges_tmp["possible_edges"]
                adtl_user_edges["new_states_included"] += adtl_user_edges_tmp["new_states_included"]
                adtl_user_edges["new_edges_included"] += adtl_user_edges_tmp["new_edges_included"]

                # if new states were discovered
                if len(adtl_user_edges_tmp['new_states_included']) > 0:
                    # update the user nodes
                    user_node_ids_copy += [idx_copy]
                    user_node_ids_copy += adtl_user_edges_tmp['new_states_included']
                    user_node_ids_copy.sort()
                # break the loop and move onto the next node to test
                elif primary_connection:
                    break

                # set flag to false after first iteration
                primary_connection = False

            # record all states/actions discovered for state id: idx
            potential_improvements[idx] = adtl_user_edges

        return potential_improvements

    @staticmethod
    def _print_user_path(graph, path, additional_spaces=0):
        """Print the path a user would take for a particular user graph

        Args:
            graph: networkx graph representing the user state graph.
            path: list of state_ids
            additional_spaces: integer for the additional space chars for each line

        Returns:
            print_lines: list of lines to print to the report
        """

        elements = []
        actions = []

        # formatting the values for easy printing
        for i in range(len(path) - 1):
            actions_list = []
            for j in graph[path[i]][path[i + 1]]:
                actions_list.append(graph[path[i]][path[i + 1]][j]['action'])
            actions.append(actions_list)
            elements.append(graph[path[i]][path[i + 1]][j]['element'])

        # easy print!
        spaces = " " * additional_spaces
        print_lines = []
        for i in range(len(path[:-1])):
            print_lines.append(f"{spaces}at state {path[i]}:")
            print_lines.append(f"{spaces}   - navigate to '{elements[i]}'")
            print_lines.append(
                f"{spaces}   - fire any one of these actions below to get to state {path[i + 1]}:")
            for action in actions[i]:
                print_lines.append(f"{spaces}      - '{action}'")

        return print_lines

    def _elements_to_fix(self, potential_improvements, user):
        """Finds elements and the states that would become accessible if the
        elements were accessible

        Args:
            potential_improvements: dict output from find_all_accessible()
            user: str denoting a crawl user

        Returns:
            improve_elements_dict: dictionary of (element,state_ids) pairs
            print_lines : list of lines to print to the report
        """

        # Getting the user graph
        user_graph = self.users["crawl_users"][user]["graph"]

        # finding elements that can be fixed
        improve_elements_dict = dict()
        for state_id, analysis_dict in potential_improvements.items():

            for i in analysis_dict['possible_edges']:
                new_edge = self.full_graph[i[0]][i[1]][i[2]]
                if user_graph.has_node(i[0]) and nx.has_path(user_graph, 0, i[0]):
                    shortest_path = nx.shortest_path(user_graph, 0, i[0])
                if new_edge['element'] in improve_elements_dict:
                    improve_elements_dict[new_edge['element']]['new_states_included'].update(analysis_dict['new_states_included'])
                    improve_elements_dict[new_edge['element']]['paths'].append(shortest_path)
                else:
                    improve_elements_dict[new_edge['element']] = {'new_states_included': set(analysis_dict['new_states_included'])}
                    improve_elements_dict[new_edge['element']]['paths'] = [shortest_path]

        # pretty-print the results
        print_lines = list()
        print_lines.append(f'**{len(improve_elements_dict.items())}** inaccessible elements for this user:\n')
        for problem_element in improve_elements_dict.keys():
            print_lines.append(f' * `{problem_element}`')
            improve_elements_dict[problem_element]["new_states_included"] = list(improve_elements_dict[problem_element]["new_states_included"])
        for problem_element, new_states_dict in improve_elements_dict.items():
            print_lines.append(f'\n#### `{problem_element}`')
            print_lines.append(f'\nMake `{problem_element}` accessible and the following states will become accessible:\n')
            for state_id in sorted(list(new_states_dict['new_states_included'])):
                if self.dom_path is not None:
                    print_lines.append(f' * {self._state_link(state_id, self.dom_path)}')
                else:
                    print_lines.append(f' * {state_id}')

            if any([len(path) > 1 for path in new_states_dict['paths']]):
                print_lines.append(f'\n`{problem_element}` appears inaccessible after the following progressions:\n')
                for path in new_states_dict['paths']:
                    if len(path) > 1:
                        if self.dom_path is not None:
                            print_lines.append(f'--> {self._state_link(path[-1], self.dom_path)}:\n')
                        else:
                            print_lines.append(f'--> state {path[-1]}:\n')

                        print_lines += self._print_user_path(user_graph, path, 4)
                        print_lines.append('')
            else:
                if self.dom_path is not None:
                    print_lines.append(f'\n`{problem_element}` only appears inaccessible at {self._state_link(0, self.dom_path)}.')
                else:
                    print_lines.append(f'\n`{problem_element}` only appears inaccessible at state 0.')

        self.report_data["accessibility"][user] = improve_elements_dict

        return improve_elements_dict, print_lines

    @staticmethod
    def _state_link(state_idx, path):
        """Returns a markdown hyperlink to open a state dom link for a given state

        Args:
            state_idx: int of the state id
            path: path where the doms are stored

        Returns:
            md_link: str for a dom state file link
        """

        url = pathlib.Path(path) / f"state-{state_idx}.html"
        # windows link
        if os.name == 'nt':
            md_link = f"[state {state_idx}]({url.absolute()})"
        # unix/linux link
        else:
            md_link = f"[state {state_idx}](file://{url.absolute()})"

        return md_link

    @staticmethod
    def _get_xpath_sim_score(xpath1, xpath2):
        """Get similarity score [0,1] between two xpaths. A score of 0 refers to
        No similarity in top-down parents. A score of 1 represents identitical
        xpaths.

        Args:
            xpath1: str representing one xpath
            xpath2: str representing another xpath

        Returns:
            score: float representing the similarity of the two xpaths
        """

        # Parse xpaths into lists and save them as the longer or shorter one
        xpath1_parsed = xpath1.split("/")
        xpath2_parsed = xpath2.split("/")
        if len(xpath1_parsed) >= len(xpath2_parsed):
            longer = xpath1_parsed
            shorter = xpath2_parsed
        else:
            shorter = xpath1_parsed
            longer = xpath2_parsed

        # Find the number of parents that are the same
        num_same_parents = 0
        for i in range(len(shorter)):
            # Equal elements, save the number of parents that are the same
            if longer[i] == shorter[i]:
                num_same_parents = i + 1
            # Unequal. End iterating
            else:
                break

        # Return ratio to bound scores between [0,1]
        score = num_same_parents / len(longer)
        return score

    def _add_xpath_edges_for_node1(self, nodes_compare_set, xpath_scores_dict,
                                   G, min_weight, xpath_node1, unique_out_nodes,
                                   source_node_out_edges):
        """Helper method for _add_xpath_edge_weights() to find the max xpath
        score between xpath_node1 and all other nodes that source_node points to
        (in _add_xpath_edge_weights()). Then insert that max xpath score into
        the weight for an xpath_edge.

        Args:
            nodes_compare_set: set of node two-tuples that have already been
                               compared
            xpath_scores_dict: dict of pairs of xpaths and their scores
            G: networkx graph to add xpath weights to
            min_weight: minimum weight to add to any edge
            xpath_node1: int ID of the first node to get xpaths from
            unique_out_nodes: set of node IDs that source_node points to
            source_node_out_edges: list of edges that come from source_node

        Returns:
            G: networkx graph (updated) with additional edges and edge weights.
            nodes_compare_set: set (updated) of node two-tuples that have
                               already been compared
            xpath_scores_dict: dict (updated) of pairs of xpaths and their
                               scores
        """

        # get unique xpaths for source_node to xpath_node1
        els_for_n = {edge[2]["element"] for edge in source_node_out_edges if
                     edge[1] == xpath_node1}

        for xpath_node2 in unique_out_nodes - {xpath_node1}:

            nodes_pair = tuple(sorted((xpath_node1, xpath_node2)))
            if nodes_pair in nodes_compare_set:
                continue

            nodes_compare_set.add(nodes_pair)
            # get unique xpaths for source_node to xpath_node2
            els_for_other_n = {edge[2]["element"] for edge in
                               source_node_out_edges if
                               edge[1] == xpath_node2}

            # compare all possible pairs of xpaths and record highest score
            max_score = min_weight
            for el1, el2 in itertools.product(els_for_n,
                                              els_for_other_n):
                # Get the xpath_score if we have already computed it,
                #  otherwise compute it and store it to reduce future
                #  computations
                xpath_tuple = tuple(sorted([el1, el2]))
                if xpath_tuple in xpath_scores_dict:
                    score = xpath_scores_dict[xpath_tuple]
                else:
                    score = self._get_xpath_sim_score(el1, el2)
                    xpath_scores_dict[xpath_tuple] = score
                if score > max_score:
                    max_score = score

            # If no edges exist between xpath_node1 and xpath_node2, add an edge
            #  with that weight, otherwise, update the score if the max_score is
            #  greater than the existing score.
            for node1, node2 in [[xpath_node1, xpath_node2], [xpath_node2, xpath_node1]]:
                edges = G.get_edge_data(node1, node2)
                if edges is None:
                    G.add_edge(node1, node2, is_xpath_edge=True,
                               xpath_edge_weight=max_score)
                # Else, update the xpath_edge_weight for all edges between
                #  node1 and node2
                else:
                    for edge in edges:
                        if G[node1][node2][edge]["xpath_edge_weight"] < max_score:
                            G[node1][node2][edge]["xpath_edge_weight"] = max_score

        return nodes_compare_set, xpath_scores_dict, G

    def _add_xpath_edge_weights(self, G, min_weight=0.2):
        """Add edges to a graph (G) for nodes that have edges from the same
        incoming node.

        Add edge weights to these edges based on max(xpath_score, min_weight),
        where pairs of xpaths (from edge elements) are compared if they exist in
        the same state and are used to transition to different states. Give
        existing edges a weight of min_weight.

        Args:
            G: networkx graph to add xpath weights to
            min_weight: minimum weight to add to any edge

        Returns:
            G: networkx graph with additional edges and edge weights.
        """

        # Tracks pairs of xpaths and their scores
        xpath_scores_dict = dict()
        # Tracks pairs of nodes that have already have xpath_edge created
        nodes_compare_set = set()

        # prep graph for existing edges
        nx.set_edge_attributes(G, False, "is_xpath_edge")
        nx.set_edge_attributes(G, min_weight, "xpath_edge_weight")

        # iterate through each node
        node_ids = list(G.nodes())
        for source_node in node_ids:
            # Get all edges the come out of node source_node
            source_node_out_edges = list(G.out_edges(nbunch=source_node, data=True))
            source_node_out_edges = [edge for edge in source_node_out_edges if
                                     edge[2]["is_xpath_edge"] is False]
            unique_out_nodes = {edge[1] for edge in source_node_out_edges}
            # iterate through the nodes that source_node points to
            for xpath_node1 in unique_out_nodes:

                # Connect xpath_node1 with other nodes that source_node points
                #  to with their max xpath score. Manage changes in returns
                returns = self._add_xpath_edges_for_node1(nodes_compare_set,
                                                          xpath_scores_dict,
                                                          G,
                                                          min_weight,
                                                          xpath_node1,
                                                          unique_out_nodes,
                                                          source_node_out_edges)
                nodes_compare_set, xpath_scores_dict, G = returns

        return G

    def _save_network_layouts(self):
        """Save network layouts to self.full_graph. These will be outputted to
        the analyzed gml file.
        """

        # Set values for network layouts and minimum edge weights
        funcs = [nx.fruchterman_reingold_layout, nx.kamada_kawai_layout]
        min_weights = [0.0, 0.2, 0.4, 0.6, 0.8]

        # Iterate through the values of xpath_edge_weight, creating xpath_edge_weight
        for min_weight in min_weights:
            G_copy = self.full_graph.copy()
            G_copy = self._add_xpath_edge_weights(G_copy, min_weight)
            coords_list = []
            titles = []
            # Iterate through the network layout functions
            for func in funcs:
                # Getting x,y positions
                pos = func(G_copy, weight="xpath_edge_weight")
                coords_list.append(pos)

                # Saving titles for plots and saved node attribute
                if func == nx.fruchterman_reingold_layout:
                    title = f"fr_{min_weight}"
                else:
                    title = f"kk_{min_weight}"
                titles.append(title)

                # Saving x,y pairs to the full graph
                x = {k: v[0] for k, v in pos.items()}
                y = {k: v[1] for k, v in pos.items()}
                nx.set_node_attributes(self.full_graph, x,
                                       f'x_{title.replace("0.", "")}')
                nx.set_node_attributes(self.full_graph, y,
                                       f'y_{title.replace("0.", "")}')

            # Plotting network layouts
            out_path = pathlib.Path(self.output_path) / "network_layouts/"
            out_path.mkdir(parents=True, exist_ok=True)
            for func, pos, title in zip(funcs, coords_list, titles):
                plt.figure()
                plt.title(title)
                nx.draw(self.full_graph, pos=pos, with_labels=True)
                plt.savefig(str(out_path / f"{title}.png"))

    @staticmethod
    def parse_color_string(color_str):
        """ Gets the colors from a style string 

        Find the color strings then return the numbers as a list
        E.g., '2px solid rgb(123,12,4)' => ['123', '12', '4']

        Args:
            color_str: The style string that contains a color

        Returns:
            List of the style numbers. Note it will have len 3 for rgb and len 4 for rgba
        """


        # Matches strings of the type rgb(ddd, dd, d), and accounts for their
        # being 1-3 numbers, and also wierd whitespace potentially
        rgb_regex = "rgb\(\s*[0-9]+,\s*[0-9]+,\s*[0-9]+\)"
        # Matches strings of the form rgba(ddd, d, d, d) or rgba(ddd, d, d, 0.d*)
        # Accounts for alpha being 1 or some random decimal
        rgba_regex = "rgba\(\s*[0-9]+,\s*[0-9]+,\s*[0-9]+,\s*[0-9]+\.*[0-9]*\)"

        if color_str.find("rgb(") > -1:
            r = re.search(rgb_regex, color_str)
            return [int(c) for c in r.group(0)[4:-1].split(",")]
        elif color_str.find("rgba(") > -1:
            r = re.search(rgba_regex, color_str)
            split = r.group(0)[5:-1].split(",")
            rgb = [int(c) for c in split[0:3]]
            return rgb + [float(split[3])] # Alpha value likely to be decimal

        return None

    @staticmethod
    def order_is_valid(prev_el, current_el):
        """ Checks if the elements follow the left to right, up to down tab order 
        
        Args:
            prev_el: The element that is getting tabbed OFF of
            current_el: The element now receiving focus

        Returns:
            True or False depending on if the elements follow logical order
        """
        x_invalid = prev_el["position"]["x"] >= current_el["position"]["x"]
        y_invalid = prev_el["position"]["y"] >= current_el["position"]["y"]
        if x_invalid and y_invalid:
            return False
        return True

    @staticmethod
    def border_is_visible(style):
        """ Takes css style determines if the style would appear visible on the screen
        
        Args:
            style - The css style rule

        Returns:
            True or false depending if the style would be visible
        """
        # # Checks if the style exists, and if so checks if the styling is visible
        # # i.e., not "rgb(0,0,0) none 0px" or ""
        # TODO: What other ways could the border be invisible?
        # Don't care about it matching the background since that will be 
        # caught by color contrast checks
        return not(style == "" or "0px" in style or "none" in style)

    @staticmethod
    def border_is_sufficient(before_border, focus_border, other_border, parent_background, min_border_contrast=1.5):
        """ Checks if the border of an element changed sufficiently

        Args:
            before_border: The border of the element before getting focus
            focus_border: The border of the element after getting focus
            other_border: Seperate border that may interfere. For example, the outline and border styles
                can be used together. So we need to compare outline against border and vice versa.
            parent_background: The background of the parent element after focus
            min_border_contrast: The contrast change from before to focused to consider sufficient

        Returns:
            True or False depending on if border is considered to have sufficient change
        """

        # Is the border is not visible after focus then it cannot be sufficient
        if not WebAccessAnalyzer.border_is_visible(focus_border):
            return False

        # Border must be visible during focus

        compare_styles = []

        # TODO: If the color is using alpha, we should integrate with 
        # the parent element background to determine the true color

        # Only compare to borders that exist and are visible
        if WebAccessAnalyzer.border_is_visible(before_border):
            compare_styles.append(before_border)

        if WebAccessAnalyzer.border_is_visible(other_border):
            compare_styles.append(other_border)

        compare_styles.append(parent_background)

        focus_color = WebAccessAnalyzer.parse_color_string(focus_border)        
        for style in compare_styles:
            style_color = WebAccessAnalyzer.parse_color_string(style)
            if color_contrast_ratio(focus_color, style_color) < min_border_contrast:
                return False

        return True

    def _state_tab_analysis(self, min_contrast=1.5, text_contrast=4.5):
        """Analyzes the tab_dict to check a visible indication of focus and if
        states have a valid and logical tab order.

        Args:
            min_contrast: float minimum contrast for valid visible
                                 indication (default is 1.5)

        Returns:
            print_lines: list of lines to print to the report
        """

        # Set up lines to print to the report
        print_lines = list()
        label = self._build_sections["els_states"]["label"]
        print_lines.append(f'\n## <a name="els_states"></a> {label}')

        # Initialize dicts to track issues at states
        problem_borders = defaultdict(list)
        keyboard_traps = dict()

        # Load in state fields json to check valid tab order
        states_valid_tab_order = []
        states_num_els = []
        unique_el_xpaths = set()
        for state_id in range(len(self.full_graph.nodes())):

            if self.full_graph.nodes(data="stub")[state_id] == "True":
                continue

            # Track xpaths used in outgoing edges from state_id
            for _, _, data in self.full_graph.out_edges(state_id, data=True):
                unique_el_xpaths.add(data["element"])

            # Load in state fields
            path = pathlib.Path(self.output_path)
            fp = path / "states" / f"state-fields-{state_id}.json"
            with open(fp) as f:
                state_fields = json.load(f)

            # Check valid tab order
            valid_tab_order = True
            # Loop over each element in state and track number of elements, 
            #  elements with border problems, and valid tab orders
            #  NOTE: we do not consider the "/html/body" element because the selenium
            #  header can be registered as "/html/body", which can cause some ill 
            #  effects. 
            tab_els_by_index = state_fields["tab_els_by_index"]
            tab_dict = state_fields["tab_dict"]
            num_els = 0
            keyboard_trap_el = None
            for i in range(len(tab_els_by_index)):
                
                current_el_xpath = tab_els_by_index[i]
                prev_el_xpath = tab_els_by_index[i-1]

                # There shouldn't be anyway for the xpath to exist in one without the other
                current_el = tab_dict[current_el_xpath]
                prev_el = tab_dict[prev_el_xpath]

                if current_el_xpath == "/html/body":
                    continue

                num_els += 1

                # First loop, there is no previous element so consider tab_order valid
                # Don't consider tab order when previous element was /html/body
                if i > 0 and prev_el_xpath != "/html/body" and not WebAccessAnalyzer.order_is_valid(prev_el, current_el):
                    valid_tab_order = False

                # Record presence keyboard trap
                if current_el.get("num_visits", 1) == 3:
                    # If the second to last item is the body, take the el after
                    if tab_els_by_index[-2] == "/html/body":
                        keyboard_trap_el = tab_els_by_index[-1]
                    else:
                        keyboard_trap_el = tab_els_by_index[-2]

                unfocused_style = current_el["unfocused_style_info"]
                focused_style = current_el["focused_style_info"]

                # Skip iteration if either styles are missing
                if unfocused_style is None or focused_style is None:
                    styles = [(unfocused_style, "unfocused_style"),
                              (focused_style, "focused_style_info")]
                    for style in styles:
                        if style[0] is None:
                            logger.warning(f"{style[1]} is missing for "
                                           f"(state_id, element): ({state_id}, "
                                           f"\"{current_el_xpath}\"). Skipping "
                                           f"tab analysis for this element.")
                    continue

                # Styles are exactly the same before and after focus
                style_unchanged = unfocused_style == focused_style

                # Check if the outline, border, or background have sufficiently changed
                outline_change_sufficient = False
                if unfocused_style["outline-style"] != focused_style["outline-style"]: # Outline has changed
                    outline_change_sufficient = WebAccessAnalyzer.border_is_sufficient(unfocused_style["outline-style"], focused_style["outline-style"], \
                        unfocused_style["border-style"], focused_style["parent-background"], min_contrast)

                border_change_sufficient = False
                if unfocused_style["border-style"] != focused_style["border-style"]: # Border has changed
                    border_change_sufficient = WebAccessAnalyzer.border_is_sufficient(unfocused_style["border-style"], focused_style["border-style"], \
                        unfocused_style["outline-style"], focused_style["parent-background"], min_contrast)

                background_change_sufficient = False
                if unfocused_style["el-background"] != focused_style["el-background"]: # Background has changed
                    before_el_back_col = WebAccessAnalyzer.parse_color_string(unfocused_style["el-background"])
                    focus_el_back_col = WebAccessAnalyzer.parse_color_string(focused_style["el-background"])
                    text_col = WebAccessAnalyzer.parse_color_string(focused_style["el-color"])

                    # Has the background color changed significantly and is the color contrast with the text still good?
                    if color_contrast_ratio(before_el_back_col, focus_el_back_col) > min_contrast and \
                        color_contrast_ratio(focus_el_back_col, text_col) > text_contrast:
                        background_change_sufficient = True

                # If the style didn't change, or none of the changes were sufficient
                changes_insufficient = not any([outline_change_sufficient, border_change_sufficient, background_change_sufficient])
                if style_unchanged or changes_insufficient:
                    if not state_id in problem_borders[current_el_xpath]:

                        # Only record if the element is visible
                        tree = self.state_tree(state_id)
                        xe_list = tree.xpath(current_el_xpath)
                        if len(xe_list) == 0:
                            logger.warning(f"Found border issue for (state, "
                                           f"element): ({state_id}, "
                                           f"{current_el_xpath}), but that "
                                           f"element does not exist in the dom."
                                           f" Skipping this element.")
                            continue
                        xe = xe_list[0]
                        reachable = xe.attrib.get("demod_reachable")
                        if reachable == "true":
                            problem_borders[current_el_xpath].append(state_id)

            # append variables for state
            states_valid_tab_order.append(valid_tab_order)
            states_num_els.append(num_els)
            if keyboard_trap_el is not None:
                keyboard_traps[state_id] = keyboard_trap_el

        # Tracking values computed
        metrics = dict()
        num_valid_tab_states = sum(states_valid_tab_order)
        num_states = len(states_valid_tab_order)
        metrics["num_valid_tab_states"] = num_valid_tab_states
        metrics["num_states"] = num_states
        metrics["els_with_problem_borders"] = problem_borders
        metrics["keyboard_traps"] = keyboard_traps

        # Defensive divide by zero
        if len(states_num_els) > 0:
            metrics["avg_num_els_per_state"] = sum(states_num_els) / len(states_num_els)
        else:
            metrics["avg_num_els_per_state"] = 0
        metrics["unique_el_xpaths"] = list(unique_el_xpaths)

        # Save metrics data for eventual output
        self.report_data["els_states"] = metrics

        # Write the high-level metrics to the report
        print_lines.append(f' * **{round(100 * metrics["num_valid_tab_states"] / metrics["num_states"],4)}% states** (not including stub states) have a valid tab order **({metrics["num_valid_tab_states"]} / {metrics["num_states"]})**\n')
        if len(problem_borders) > 0:
            print_lines.append(f' * **{len(problem_borders)} elements** have issues with visual indication of focus. See field `["els_states"]["els_with_problem_borders"]` in `{self._json_data_fname}` for those elements and the states they affect.\n')
        else:
            print_lines.append(f' * **No elements have issues with visual indication of focus**')

        return print_lines

    def _violations(self):
        """Compiles and saves violations ID'd by state and element for ingestion
        in the web app.

        Note: this function calls all other functions in this class that start
        with "_sc_" to compile violations by various success criteria.
        """

        # Get success criterion methods
        sc_methods = [method_name for method_name in dir(self)
                      if method_name[:4] == "_sc_"]

        screenshot_path = pathlib.Path(self.output_path) / "screenshots"

        # Iterate through the full graph and send each node through to each
        #  helper sc method to get all atomic violations
        all_violations = defaultdict(lambda: defaultdict(list))
        for state_id in self.full_graph.nodes():
            # Initialize the dict for this state
            state_screenshot_path = str(screenshot_path / f"state-{state_id}.png")
            all_violations[state_id]["src"] = state_screenshot_path

            # Get all violations for transitions into this state
            source_violations = []
            for sc_method in sc_methods:
                source_violations += getattr(self, sc_method)(state_id)

            # Add violations to the source state only if we haven't already
            #  tracked them (necessary when there are multiple actions from
            #  state_id to another state, typically when all violate a rule)
            for (source_id, violation) in source_violations:
                if violation not in all_violations[source_id]["violations"]:
                    all_violations[source_id]["violations"].append(violation)

        # Form composite violations
        composite_violations = defaultdict(list)
        tree = self._create_tree_from_graph(self.full_graph)
        state_errors = {state_id: len(state_dict["violations"])
                        for state_id, state_dict in all_violations.items()}
        for state in tree.nodes():
            for out_state in tree[state].keys():  # Gets a dictionary of edges for this state
                num_subtree_issues = self._find_num_subtree_issues(out_state, tree, state_errors)
                # We only care if some issues are found
                if num_subtree_issues > 0:
                    # Get edge data associated with the desired xpath
                    xpath = tree.get_edge_data(state, out_state)["element"]
                    for k, v in self.full_graph.get_edge_data(state, out_state).items():
                        if v["element"] == xpath:
                            data = v
                            break
                    # Save composite violation
                    composite_violations[state].append({
                        "type": "composite",
                        # TODO improvement: use "warning" if all violations
                        #  under this composite violation are warnings. If there
                        #  is at least 1 error, we should bump this to "error"
                        "level": "warning",
                        "element": self._get_element_data(data),
                        "num_issues": num_subtree_issues,
                        "state_link": out_state
                    })

        # Convert to dict and add in missing fields
        clean_all_violations = dict()
        for state_id, violations in composite_violations.items():
            all_violations[state_id]["violations"] += violations
        for state_id, state_dict in all_violations.items():
            clean_all_violations[state_id] = dict(state_dict)
            if "violations" not in clean_all_violations[state_id]:
                clean_all_violations[state_id]["violations"] = list()

        # Save to file
        fpath = pathlib.Path(self.output_path) / "element_map.json"
        self._to_json(fpath, clean_all_violations)

    def _sc_2_5_5(self, state_id):
        """Finds violations of WCAG SC 2.5.5 (target size) in getting to state
        with id state_id.

        Args:
            state_id: int id of the state to find violations going into

        Returns:
            source_violations: dict of source: violation the details the source
                               node and violation to record
        """

        # Are there any exceptions simply based on the tag name?
        tag_exceptions = set()

        source_violations = list()

        # We only want to throw violation for an xpath once per state
        bad_xpaths = set()

        for source, _, data in self.full_graph.in_edges(state_id, data=True):
            # Skip if we are not using the mouse
            if data["action"] not in self._mouse_actions_str:
                continue
            # Skip if the element is an exception or the it's an inline link
            xpath = data["element"]
            parent_el = os.path.basename(os.path.dirname(xpath))
            inline = data["tag_name"] == "a" and parent_el == "p"
            if data["tag_name"] in tag_exceptions or inline:
                continue

            if data["width"] < 44 or data["height"] < 44:
                if xpath not in bad_xpaths:
                    bad_xpaths.add(xpath)
                    element = self._get_element_data(data)
                    replay = self.full_graph.nodes(data=True)[source]["paths"].split(",")[0]

                    # Get the code from the dom tree
                    lel = self.state_tree(source).xpath(element["xpath"])[0]
                    code = etree.tostring(lel, encoding="unicode")

                    violation = self._format_violation(type="atomic",
                                                       level="warning",
                                                       category="S.C. 2.5.5",
                                                       element=element,
                                                       replay=replay,
                                                       code=code)

                    # 2-tuple that defines (1) the state the violation should be
                    #  put on and (2) the violation
                    source_violations.append((source, violation))
            else:
                # We have found a way to get from source to state_id with a
                #  mouse that has a large enough target. Report no violations.
                # TODO should we exit early if there is at least one way to get
                #  to state_id that satisfies this criterion?
                return list()

        # Iterate the group id if we are returning violations
        if len(source_violations) > 0:
            self._group_id += 1

        return source_violations

    def _sc_2_1_1(self, state_id):
        """Finds violations of WCAG SC 2.1.1 (Keyboard Interactive Violation) in
        getting to state with id state_id.

        Args:
            state_id: int id of the state to find violations going into

        Returns:
            source_violations: dict of source: violation the details the source
                               node and violation to record
        """

        # Record an error for all incoming edges if we can't go to state_id with
        #  any keyboard action
        source_violations = list()
        for source, _, data in self.full_graph.in_edges(state_id, data=True):
            if data["action"] in self._keyboard_actions_str:
                # TODO should we exit early if there is at least one way to get
                #  to state_id that satisfies this criterion?
                return list()

            element = self._get_element_data(data)
            replay = self.full_graph.nodes(data=True)[source]["paths"].split(",")[0]

            # Get the code from the dom tree
            lel = self.state_tree(source).xpath(element["xpath"])[0]
            code = etree.tostring(lel, encoding="unicode")

            violation = self._format_violation(type="atomic",
                                               level="error",
                                               category="S.C. 2.1.1",
                                               element=element,
                                               replay=replay,
                                               code=code)

            # 2-tuple that defines (1) the state the violation should be put
            #  on and (2) the violation
            source_violations.append((source, violation))

        # Iterate the group id if we are returning violations
        if len(source_violations) > 0:
            self._group_id += 1

        return source_violations

    def _sc_2_4_7(self, state_id):
        """Finds violations of WCAG SC 2.4.7 (Focus Visible) in getting to state
        with id state_id.

        Args:
            state_id: int id of the state to find violations on

        Returns:
            source_violations: dict of source: violation the details the source
                               node and violation to record
        """

        # Record an error for all outgoing edges if we can't go to state_id with
        #  any keyboard action
        source_violations = list()

        prob_bords = self.report_data["els_states"]["els_with_problem_borders"]
        replay = self.full_graph.nodes(data=True)[state_id]["paths"].split(",")[0]
        for xpath, list_of_states in prob_bords.items():
            # Only record it for the first state found with the issue
            if len(list_of_states) == 0 or state_id != min(list_of_states):
                continue

            element = self._get_element_data_backup(state_id, xpath)

            # Get the code from the dom tree
            lel = self.state_tree(state_id).xpath(xpath)[0]
            code = etree.tostring(lel, encoding="unicode")

            # Format the violation
            violation = self._format_violation(type="atomic",
                                               level="error",
                                               category="S.C. 2.4.7",
                                               element=element,
                                               replay=replay,
                                               code=code)

            # 2-tuple that defines (1) the state the violation should be put
            #  on and (2) the violation
            source_violations.append((state_id, violation))

        # Iterate the group id if we are returning violations
        if len(source_violations) > 0:
            self._group_id += 1

        return source_violations

    def _sc_2_4_3(self, state_id):
        """Finds violations of WCAG SC 2.4.3 (Focus Order) in getting to state
        with id state_id.

        Args:
            state_id: int id of the state to find violations on

        Returns:
            source_violations: dict of source: violation the details the source
                               node and violation to record
        """

        # Record an error for all outgoing edges if we can't go to state_id with
        #  any keyboard action
        source_violations = list()

        # Find the keyboard trap if it was already recorded for this state
        if state_id in self.report_data["els_states"]["keyboard_traps"]:
            replay = self.full_graph.nodes(data=True)[state_id]["paths"].split(",")[0]
            xpath = self.report_data["els_states"]["keyboard_traps"][state_id]

            element = self._get_element_data_backup(state_id, xpath)

            # Get the code from the dom tree
            lel = self.state_tree(state_id).xpath(xpath)[0]
            code = etree.tostring(lel, encoding="unicode")

            # Format the violation
            violation = self._format_violation(type="atomic",
                                               level="error",
                                               category="S.C. 2.4.3",
                                               element=element,
                                               replay=replay,
                                               code=code)

            # 2-tuple that defines (1) the state the violation should be put
            #  on and (2) the violation
            source_violations.append((state_id, violation))

        # Iterate the group id if we are returning violations
        if len(source_violations) > 0:
            self._group_id += 1

        return source_violations

    def _sc_1_4_3(self, state_id):
        """Finds violations of WCAG SC 1.4.3 (Minimum Contrast) in leaving state
        with id state_id.

        Args:
            state_id: int id of the state to find violations on

        Returns:
            source_violations: dict of source: violation the details the source
                               node and violation to record
        """

        # Record an error for all outgoing edges if we can't go to state_id with
        #  any keyboard action
        source_violations = list()
        if not hasattr(self, "_xpaths_contrast_violations"):
            self._xpaths_contrast_violations = set()
        for _, target, data in self.full_graph.out_edges(state_id, data=True):
            # Check for standard minimum contrast ratio
            if data["contrast_ratio"] >= 4.5:
                continue
            # Check for large text minimum contrast ratio
            if data["contrast_ratio"] >= 3.0 and data["font_size"] >= 18:
                continue
            # Element has already been added to the list of violations
            if data["element"] in self._xpaths_contrast_violations:
                continue

            # Element did not pass either minimums and hasn't already been
            #  added -- record violation
            element = self._get_element_data(data)
            replay = self.full_graph.nodes(data=True)[state_id]["paths"].split(",")[0]

            # Get the code from the dom tree
            lel = self.state_tree(state_id).xpath(element["xpath"])[0]
            code = etree.tostring(lel, encoding="unicode")

            violation = self._format_violation(type="atomic",
                                               level="error",
                                               category="S.C. 1.4.3",
                                               element=element,
                                               replay=replay,
                                               code=code)

            # 2-tuple that defines (1) the state the violation should be put
            #  on and (2) the violation
            source_violations.append((state_id, violation))
            self._xpaths_contrast_violations.add(element["xpath"])

        # Iterate the group id if we are returning violations
        if len(source_violations) > 0:
            self._group_id += 1

        return source_violations

    def _format_violation(self, type, level, category, element, replay=None,
                          code=None, num_issues=None, state_link=None):
        """Helper function to format a violation dictionary.

        NOTE: replay and code are only used for atomic violations, whereas
        num_issues and state_link are only used for composite violations.

        Args:
            type: str in {"atomic", "composite"}
            level: str in {"warning", "error"}
            category: str denoting the WCAG (or other) standard/criterion
            element: str xpath denoting the element
            replay: None or str that describes how a user tries the action on el
            code: None or str HTML code for the element
            num_issues: None or int number of issues contained on and downstream of state state_link
            state_link: None or int state id where the composite violations live

        Returns:
            source_violations: dict of source: violation the details the source
                               node and violation to record
        """

        # Save the base fields
        assert type in {"atomic", "composite"}, "type needs to be 'atomic' " \
                                                "or 'composite'"
        assert level in {"warning", "error"}, "level needs to be 'warning' " \
                                              "or 'error'"
        violation = {"type": type, "level": level, "category": category,
                     "element": element, "group_id": self._group_id}

        # Save the other fields only if they are not None
        fields = {"replay", "code", "num_issues", "state_link"}
        for field in fields:
            if eval(field) is not None:
                violation[field] = eval(field)

        return violation

    # --
    # Private methods to format analyzed sections of the report.
    #   May be overridden.
    #

    def _analyze_crawl_user(self, user):
        print_lines = super()._analyze_crawl_user(user)
        inacc_analysis_print_lines = self._inaccessible_user_analysis(user)
        print_lines += inacc_analysis_print_lines

        return print_lines

    def _analyze_build(self):
        print_lines = super()._analyze_build()
        self._save_network_layouts()
        print_lines += self._state_tab_analysis()
        self._violations()
        return print_lines

    # --
    # Public utility functions.
    #   May be overridden.
    #

    def plot_graphs(self):
        """Plotting the full graph and for each crawl_user, their: graph, graph
        of nodes/edges inaccessible, and graph of nodes/edges that are
        theoretically accessible.

        Note: the last graph for each user contains a subgraph of accessible
        edges based on the actions that the user can perform. This would include
        subsets of edge that may be in an inaccessible region of the graph, but
        have the necessary actions (found by the OmniUser) to be accessible if
        they were able to be reached.
        """

        print("Full graph:")
        nx.draw(self.full_graph, pos=graphviz_layout(self.full_graph),
                with_labels=True)
        plt.show()

        for user in self.users["crawl_users"].keys():
            print(f"{user}'s graph:")
            nx.draw(self.users["crawl_users"][user]["graph"],
                    pos=graphviz_layout(self.full_graph), with_labels=True)
            plt.show()

            print(f"graph inaccessible to {user}:")
            inaccessible_graph = self._get_inaccessible_graph(user)
            nx.draw(inaccessible_graph, pos=graphviz_layout(self.full_graph),
                    with_labels=True)
            plt.show()

            print(f"Full graph with only {user}-accessible nodes/edges")
            user_actions_subgraph = self._get_user_actions_subgraph(user)
            nx.draw(user_actions_subgraph, pos=graphviz_layout(self.full_graph),
                    with_labels=True)
            plt.show()

    @staticmethod
    def _create_tree_from_graph(graph):
        """Transforms graph into a tree (DAG)

        Uses BFS to create a tree from the graph where the path to each node
        is the shortest path that was found in the graph. Used for presentation
        simplification.

        Args:
            graph: networkx graph created by crawling

        Returns:
            tree: networkx Directed Acyclic Graph (DAG)
        """

        tree = nx.DiGraph()

        initial_state = 0  # Start at state 0
        tree.add_node(initial_state)
        discovered = set([initial_state])
        states_to_visit = deque()  # We append right and pop left (FIFO)
        states_to_visit.append(initial_state)

        # Use BFS to construct a DAG for use in web app
        while states_to_visit:
            current_state = states_to_visit.popleft()

            # Get all adjacent nodes to current state
            adjacent = set(graph[current_state])

            # Determine which are undiscovered
            undiscovered = adjacent - discovered

            for state in undiscovered:
                # Add the state to the tree
                tree.add_node(state)
                # Create edge between current and discovered
                tree.add_edge(current_state, state,
                              element=graph.get_edge_data(current_state, state)[
                                  0]['element']
                              )
                # Append to our states to visit
                states_to_visit.append(state)

            discovered |= undiscovered

        return tree

    @staticmethod
    def _find_num_subtree_issues(start_state, tree, state_errors):
        """Finds all issues in the tree with start state as root.

        Args:
            start_state: The root of the subtree. Issues in this state included in count
            tree: The full tree with start_state as a node
            state_errors: dict mapping state_id to number of errors

        Returns:
            sub_tree_issues: Integer number of issues found in subtree
        """

        # We want to check all children of start state for errors
        subtree_issues_found = state_errors[start_state]

        descendants = nx.descendants(tree, start_state)

        for state in descendants:
            if state in state_errors:
                subtree_issues_found += state_errors[state]

        return subtree_issues_found

    @staticmethod
    def _get_element_data(data):
        """Reformats data dictionary for an element

        Args:
            data: dict of fields describing an element from graph edge data

        Returns:
            element: dict of fields necessary for the webapp ingest
        """
        xy = json.loads(data["xy_loc"].replace("'", '"'))
        # TODO remove this defensive check for `text` once we don't care about
        #  backwards compatibility
        text = data.get("text", "")
        element = {"x": xy["x"],
                   "y": xy["y"],
                   "width": data["width"],
                   "height": data["height"],
                   "xpath": data["element"],
                   "text": text,
                   "tag": data["tag_name"]}

        return element

    def _get_element_data_backup(self, state_id, xpath):
        """Gets element from the graph, and uses the dom as a backup if it
        doesn't exist (i.e., there was no edge featuring that xpath from
        state_id to some other state).

        Args:
            state_id: int id of the state to find violations on
            xpath: str full xpath of the element we are getting the data for

        Returns:
            element: dict of fields necessary for the webapp ingest
        """
        # First try to get element data from the graph
        element = None
        for _, _, data in self.full_graph.out_edges(state_id, data=True):
            if data["element"] == xpath:
                element = self._get_element_data(data)
                break

        # If it doesn't exist, get it from the dom
        if element is None:
            tree = self.state_tree(state_id)
            xe = tree.xpath(xpath)[0]
            demod_width = xe.attrib.get("demod_width")
            demod_height = xe.attrib.get("demod_height")
            width, height = self._get_clean_width_height(xe)
            text = "" if xe.text is None else xe.text.strip()
            # int(float()) is necessary to read in floats and then round down
            element = {"x": int(float(xe.attrib.get("demod_left"))),
                       "y": int(float(xe.attrib.get("demod_top"))),
                       "width": width,
                       "height": height,
                       "xpath": xpath,
                       "text": text,
                       "tag": xe.tag}

        return element

    @staticmethod
    def _strip_ns_prefix(tree):
        """Remove namespaces from HTML tree

        See https://stackoverflow.com/questions/18159221/remove-namespace-and-prefix-from-xml-in-python-using-lxml

        Args:
            tree: raw HTML tree

        Returns:
            tree: HTML tree with namespaces removed
        """
        # iterate through only element nodes (skip comment node, text node, etc) :
        for element in tree.xpath("descendant-or-self::*"):
            # if element has prefix...
            if element.prefix:
                # replace element name with its local name
                element.tag = etree.QName(element).localname
        return tree

    @staticmethod
    def _get_clean_width_height(xe):
        """Parse out the demod-<width/height> from the lxml element.

        First tries to pull it directly from the element. If that doesn't exist
        (could be empty, could be 'auto'), then try to pull it directly from the
        parent element. If that doesn't exist, default to 0.

        Args:
            xe: lxml.etree._Element that represents the element

        Returns:
            width: int cleaned width of the lxml element
            height: int cleaned height of the lxml element
        """

        attribs = ["demod_width", "demod_height"]

        clean_vals = []
        for attrib in attribs:
            val = xe.attrib.get(attrib)
            clean_val_nums = [int(s) for s in re.findall(r'\d+', val)]
            if len(clean_val_nums) == 0:
                # No numerical value for width, trying parent el
                parent_val = xe.getparent().attrib.get(attrib)
                clean_parent_val_nums = [int(s) for s in
                                         re.findall(r'\d+', parent_val)]
                if len(clean_parent_val_nums) == 0:
                    # No numerical value for width -- defaulting to zero
                    clean_val = 0
                else:
                    # Using first parsed number in parent width
                    clean_val = clean_parent_val_nums[0]
            else:
                # Using first parsed number in width
                clean_val = clean_val_nums[0]
            clean_vals.append(clean_val)

        return clean_vals
