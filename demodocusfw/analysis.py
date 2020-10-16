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

"""Analyzes a graph output from the operations side of the framework (crawling
an application). This module represents what developers would want as a base
analysis, which should be compatible with any type of interface and application
context.

To create a custom Analyzer that inherits from BaseAnalzyer, you may need to
edit any of the following blocks. CTRL+F the names (ex: "Formatting sections")
to jump directly to these blocks of code.

Formatting sections

  - _build_sections : Stores formatting and text information for sections that
    run once per analysis. There are no build_sections implemented for the
    BaseAnalyzer, but these should not be specific to a particular user model,
    and should only be executed once per analysis. Potential examples include:
      - assessing the difficulty to reach pre-configured paths
      - complexity of network
      - consistency of information, themes, styles, across states.
  - _crawl_user_sections : Stores formatting and text information for sections that
    run once per crawl_user. Some sections that are coded into BaseAnalzyer are:
      - metrics: compares network metrics to the graph produced by the
        crawl_user compared to the build_user (see
        self._calculate_user_metrics() for the implementation).
      - paths: analyzes optimal paths between all pairs of nodes for the
        crawl_user compared to the build_user (see self.analyze_paths() for the
        implementation).
  NOTE: For any child class of BaseAnalyzer, whatever data in _build_sections
        and _crawl_user_sections will append/overwrite to all higher-level
        inherited classes. No need to copy and paste if you want to inherit
        those sections, but you may want to delete them in your class's
        customized __init__() if you do not want those higher-level sections.

Constructor/initializer

  See the doc-string for details on what this does, but if you want to track any
  additional data (ex: predefined paths, supporting files, etc) or perform other
  tasks before you analyze, this is the place to do it.

Property (getter/setter) methods

  No general advice is given here, but add methods to this block as necessary.
  You will most likely not need to override existing methods (except for the
  `data` methods).

Methods to perform section-specific analyses

  No general advice is given here, but add methods to this block as necessary.
  You will most likely not need to override existing methods.

Private methods to format analyzed sections of the report

  This is where the methods coded above get pulled to be cleanly organized into
  the report. If you implement any new section-specific methods, be sure to
  add them to these functions.

Public utility functions

  Functions that may be called in certain circumstances (ex: printing graphs
  for demo/debug), but are not typically called in the standard workflow.

"""

import collections
import json
import os
import pathlib
from types import ModuleType

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout
import numpy as np
import pandas as pd
from tabulate import tabulate

from .graph import Graph
from .user import UserModel


class BaseAnalyzer:

    # Defining filenames for output files (path is parameterized)
    _json_data_fname = "analyzed_data.json"
    _report_fname = "analysis_report.md"
    _analyzed_gml_fname = "analyzed_full_graph.gml"
    _paths_df_fname = "paths_df.csv"

    # --
    # Formatting sections. Title and guide to be printed for each section.
    #   May be overridden.
    #

    """Configure these diction

    In _build_sections and _crawl_user_sections below, the structure of the
    dictionary is to be as follows:

    <section_id> : {"label": <section_title>,
                    "guide_lines": <guide_lines>
                   }

    NOTE: The values wrapped in "" should not change, but is wrapped in <>
          should be filled with meaningful content as described below:

    section_id     -- str that uniquely identifies the section (not seen in
                      rendered report but necessary for sections to link
                      properly).
    section_title  -- str that visually represents the name of the section (what
                      the viewer of the report will see).
    guide_lines    -- list of str that describe what the section is doing in
                      the guide. Should clearly explain enough so that the
                      report is easy to understand.
    """

    _build_sections = {}

    _crawl_user_sections = \
        {
            "metrics":
                {"label": "Summary Metrics",
                 "guide_lines":
                     [
                         ' * **in-degree** -- number of edges that point into a given node',
                         ' * **out-degree** -- number of edges that point away from a given node',
                         ' * **strongly connected graph** -- for a given graph, a path exists between every pair of nodes (and in both directions)'
                     ]
                },
            "paths":
                {"label": "Path Analysis",
                 "guide_lines":
                     [
                         ' * **path** -- an ordered series of edges that connects one node to another node',
                         ' * **path length** -- number of edges in a path',
                         ' * **average path length** -- for all paths in a graph, the average of all path lengths',
                         ' * the **paths dataframe** has the following columns:',
                         '     * **idx_from** -- index/ID of the starting node for a path',
                         '     * **idx_to** -- index/ID of the ending node for a path',
                         '     * **path_incr** -- this represents how much more the shortest path length from **idx_from** to **idx_to** is for the given user compared to the BuildUser. *Example*: a value of **2** means that it takes a given user 2 more actions to get from **idx_from** to **idx_to** than it does for BuildUser. **0** is desirable, higher numbers are not',
                         '     * **dijkstra_diff** -- this represents the difference of the shortest weighted path length (using Dijkstra\'s algorithm) from **idx_from** to **idx_to** for the given user compared to the BuildUser. *Example*: a value of **0.2** means that the average score for each edge in the path from **idx_from** to **idx_to** is 0.2 lower (out of 1) for the BuildUser than it is for the CrawlUser. **0** is desirable and represents ease of accessibility, higher numbers are worse'
                     ]
                }
        }

    # --
    # Constructor/initializer. Loads in graph and sets up needed class fields.
    #   May be overridden.
    #

    def __init__(self, graph_fpath, config):
        """Loads the graph object from graph_fpath, initializes build_user and
        crawl_user graphs, and also stores the entire config for potential uses
        which can be called in any instance method. Utilizes formal
        getter/setter methods to track these objects.

        Args:
            graph_fpath: path and filename of the .gml file to analyze

        """
        # Initialize class fields to None
        self._graph_fpath = None
        self._users = None
        self._full_graph = None
        self._config = None
        self._report_data = None
        self._output_path = None

        # Set class field values
        self._init_sections()
        self.config = config
        self.graph_fpath = graph_fpath
        self._init_users()
        self.report_data = collections.defaultdict(dict)
        self.output_path = str(pathlib.Path(self.graph_fpath).parents[0])

    # --
    # Helper methods for initialization.
    #   May be overridden.
    #

    def _init_sections(self):

        # Get all members of class hierarchy (besides object base class)
        class_hierarchy = list(self.__class__.__mro__)[0:-1]

        build_sections = {}
        crawl_user_sections = {}

        # Iterate from grandest parent class to self class, updating build and
        #  crawl_user sections.
        for class_name in reversed(class_hierarchy):
            build_sections.update(class_name._build_sections)
            crawl_user_sections.update(class_name._crawl_user_sections)

        # Update sections for the self object
        self._build_sections = build_sections
        self._crawl_user_sections = crawl_user_sections

    def _init_users(self):
        """Dictionary that represents UserModels and their graphs. Has the
        structure as follows:

        {
             "build_user":  {
                                "user_model": UserModel,
                                "graph": networkx.graph
                            }
             "crawl_users": {
                                 "crawl_user_1" : {"user_model": UserModel,
                                                   "graph": networkx.graph},
                                 "crawl_user_2" : {"user_model": UserModel,
                                                   "graph": networkx.graph},
                                 ...
                            }
        }
        """
        assert self.config is not None, "the Analyzer's config has not been" \
                                        " set. Cannot continue with analysis"

        build_user = self.config.BUILD_USER
        crawl_users = self.config.CRAWL_USERS

        for user_model in [build_user] + crawl_users:
            assert isinstance(user_model, UserModel), f"user_models " \
                f"\"{user_model}\" is not a UserModel object"

        full_graph = nx.read_gml(self.graph_fpath)
        self.full_graph = full_graph

        # Storing the build_user and its relevant information
        users_dict = dict()
        users_dict["build_user"] = self._get_user_dict(build_user)

        users_dict["crawl_users"] = dict()
        for crawl_user in crawl_users:
            name = crawl_user.get_name()
            users_dict["crawl_users"][name] = self._get_user_dict(crawl_user)

        self._users = users_dict

    # --
    # Property (getter/setter) methods.
    #   May be overridden.
    #

    @property
    def graph_fpath(self):
        return self._graph_fpath

    @graph_fpath.setter
    def graph_fpath(self, graph_fpath):
        assert os.path.isfile(graph_fpath), f"graph_fpath \"{graph_fpath}\" " \
            f"is not a valid file."

        self._graph_fpath = graph_fpath

    @property
    def users(self):
        return self._users

    @property
    def full_graph(self):
        return self._full_graph

    @full_graph.setter
    def full_graph(self, full_graph):
        """Represents the graph with data for ALL users. Any fields that are
        produced by analysis and outputted to the analyzed gml file will be
        stored in this object
        """
        assert isinstance(full_graph, nx.Graph), f"full_graph " \
                                                 f"\"{full_graph}\" is not a " \
                                                 f"networkx graph"
        self._full_graph = full_graph

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        assert isinstance(config, ModuleType), "config object is not a module" \
                                               ". Cannot continue analysis."
        self._config = config

    @property
    def report_data(self):
        return self._report_data

    @report_data.setter
    def report_data(self, report_data):
        assert isinstance(report_data, collections.defaultdict), \
               "report_data must be a collections.defaultdict"
        self._report_data = report_data

    @property
    def output_path(self):
        return self._output_path

    @output_path.setter
    def output_path(self, output_path):
        assert os.path.isdir(output_path), f"output_path \"{output_path}\" " \
            f"is not a valid output directory."
        self._output_path = output_path

    # --
    # Methods to perform section-specific analyses.
    #   May be overridden.
    #

    def _calculate_user_metrics(self, user):
        """Analyzes network metrics for the user's graph, compared to the
        full graph.

        Args:
            user: str denoting a crawl user

        Returns:
            print_lines: list of lines to print to the report
        """

        # Intializing lines to print
        print_lines = list()
        section = "metrics"
        label = self._crawl_user_sections[section]["label"]
        print_lines.append(f'### <a name="{user.lower()}-{section}"></a> {label}')

        user_graph = self.users["crawl_users"][user]["graph"]

        # computing network metrics
        metrics = dict()
        metrics['crawluser_nodes'] = len(user_graph.nodes())
        metrics['builduser_nodes'] = len(self.full_graph.nodes())
        metrics['crawluser_stub_nodes'] = sum(
            [1 for n in user_graph.nodes(data=True)
             if n[1]['stub'] == 'True'])
        metrics['builduser_stub_nodes'] = sum([1 for n in self.full_graph.nodes(data=True) if n[1]['stub'] == 'True'])
        metrics['crawluser_edges'] = len(user_graph.edges())
        metrics['builduser_edges'] = len(self.full_graph.edges())
        metrics['crawluser_avg_indeg'] = round(sum(d for n, d in user_graph.in_degree()) / metrics['crawluser_nodes'], 2)
        metrics['crawluser_avg_outdeg'] = round(sum(d for n, d in user_graph.out_degree()) / metrics['crawluser_nodes'], 2)
        metrics['builduser_avg_indeg'] = round(sum(d for n, d in self.full_graph.in_degree()) / metrics['builduser_nodes'], 2)
        metrics['builduser_avg_outdeg'] = round(sum(d for n, d in self.full_graph.out_degree()) / metrics['builduser_nodes'], 2)
        metrics['crawluser_is_strongly_connected'] = nx.is_strongly_connected(user_graph)
        metrics['builduser_is_strongly_connected'] = nx.is_strongly_connected(self.full_graph)

        # Save metrics data for eventual output
        self.report_data["network_metrics"][user] = metrics

        # formatting into lines for markdown
        print_lines.append(f'**{round(100 * metrics["crawluser_nodes"] / metrics["builduser_nodes"],2)}% states** accessible compared to BuildUser **({metrics["crawluser_nodes"]} / {metrics["builduser_nodes"]})**\n')
        if metrics['builduser_stub_nodes'] > 0:
            print_lines.append(f' * **{round(100 * metrics["crawluser_stub_nodes"] / metrics["builduser_stub_nodes"],2)}% stub states** accessible compared to BuildUser **({metrics["crawluser_stub_nodes"]} / {metrics["builduser_stub_nodes"]})**\n')
        else:
            print_lines.append(f' * No **stub nodes** found in this graph\n')
        if metrics["builduser_edges"] > 0:
            print_lines.append(f'**{round(100 * metrics["crawluser_edges"] / metrics["builduser_edges"],2)}% edges** accessible compared to BuildUser **({metrics["crawluser_edges"]} / {metrics["builduser_edges"]})**\n')
        else:
            print_lines.append(f'**0.00% edges** accessible compared to BuildUser **({metrics["crawluser_edges"]} / {metrics["builduser_edges"]})**\n')
        print_lines.append(f'**{metrics["crawluser_avg_indeg"]}** average in-degree (**{metrics["builduser_avg_indeg"]}** for BuildUser)\n')
        print_lines.append(f'**{metrics["crawluser_avg_outdeg"]}** average out-degree (**{metrics["builduser_avg_outdeg"]}** for BuildUser)\n')
        print_lines.append(f'strongly connected user graph: **{metrics["crawluser_is_strongly_connected"]}**')

        return print_lines

    def _analyze_user_paths(self, user):
        """Analyzes the shortest path lengths for a user compared to the full
        graph

        Args:
            user: str denoting a crawl user

        Returns:
            paths_df: pd.DataFrame of the increased path length for a user
            print_lines: list of lines to print to the report
        """

        # Intializing lines to print
        print_lines = list()
        section = "paths"
        label = self._crawl_user_sections[section]["label"]
        print_lines.append(f'### <a name="{user.lower()}-{section}"></a> {label}')

        # initialize state_ids lists and shortest path matrices for build and user
        build_user = str(self.users["build_user"]["user_model"])
        user_graph = self.users["crawl_users"][user]["graph"]
        state_ids_user = list(user_graph.nodes())
        state_ids_build = list(self.full_graph.nodes())
        n = len(state_ids_build)
        shortest_paths_build = np.full((n, n), np.nan)
        shortest_paths_user = np.full((n, n), np.nan)
        dijkstra_paths_user = np.full((n, n), np.nan)

        # initializing scores to output
        reversed_scores = {k: 1 - v for k, v in
                           nx.get_edge_attributes(user_graph, user).items()}
        nx.set_edge_attributes(user_graph, reversed_scores, f"{user}_reversed")
        # defaulting scores for nodes
        nx.set_node_attributes(user_graph, 0, f'{user}AddScore')
        nx.set_node_attributes(user_graph, 0, f'{user}MultScore')

        # loop through and compute shortest paths for pairs of nodes for build_user
        build_add_scores = {0: 0.0}
        build_prod_scores = {0: 1}
        for i in state_ids_build:
            for j in state_ids_build:
                if i != j and nx.has_path(self.full_graph, i, j):
                    shortest_path = nx.shortest_path(self.full_graph, source=i, target=j)
                    shortest_path_length = nx.shortest_path_length(self.full_graph, i, j)
                    shortest_paths_build[int(i), int(j)] = shortest_path_length

                    add_score = 0
                    prod_score = 1
                    for k in range(len(shortest_path) - 1):
                        node1 = shortest_path[k]
                        node2 = shortest_path[k + 1]
                        score = max([v[f'{build_user}'] for k, v in
                                     self.full_graph.get_edge_data(node1, node2).items()])
                        add_score += score
                        prod_score *= score

                    # saving scores for nodes
                    if i == 0:
                        build_add_scores[j] = add_score
                        build_prod_scores[j] = prod_score

        # saving scores to nodes
        nx.set_node_attributes(self.full_graph, build_add_scores, f'{build_user}AddScore')
        nx.set_node_attributes(self.full_graph, build_prod_scores, f'{build_user}MultScore')

        # loop through and compute shortest paths for pairs of nodes for crawl_user
        add_scores = {0: 0.0}
        prod_scores = {0: 1}
        for i in state_ids_user:
            for j in state_ids_user:
                if i != j and nx.has_path(user_graph, i, j):
                    shortest_paths_user[int(i), int(j)] = \
                        nx.shortest_path_length(user_graph, i, j)
                    shortest_path = nx.dijkstra_path(user_graph, i, j,
                                                     weight=f'{user}_reversed')

                    add_score = 0
                    prod_score = 1
                    for k in range(len(shortest_path) - 1):
                        node1 = shortest_path[k]
                        node2 = shortest_path[k + 1]
                        score = max([v[f'{user}'] for k, v in
                                     user_graph.get_edge_data(node1, node2).items()])
                        add_score += score
                        prod_score *= score

                    dijkstra_paths_user[int(i), int(j)] = add_score

                    # saving scores for nodes
                    if i == 0:
                        add_scores[j] = add_score
                        prod_scores[j] = prod_score
        # saving scores to nodes
        nx.set_node_attributes(user_graph, add_scores, f'{user}AddScore')
        nx.set_node_attributes(user_graph, prod_scores, f'{user}MultScore')

        # Updating the full graph with cummulative Add and Mult scores for the
        #  given user
        self.users["crawl_users"][user]["graph"] = user_graph
        nx.set_node_attributes(self.full_graph, 0, f'{user}AddScore')
        nx.set_node_attributes(self.full_graph, 0, f'{user}MultScore')
        add_dict = dict(user_graph.nodes(data=f'{user}AddScore'))
        mult_dict = dict(user_graph.nodes(data=f'{user}MultScore'))
        nx.set_node_attributes(self.full_graph, add_dict, f'{user}AddScore')
        nx.set_node_attributes(self.full_graph, mult_dict, f'{user}MultScore')

        # get path differences for active user edges
        paths_diff = np.sum(np.stack([-shortest_paths_build,
                                      shortest_paths_user]),
                            axis=0)
        # we are assuming that the dijkstra's distance for the BuildUser is always
        # the number of edges it has to traverse because the BuildScore is always 1
        dijkstra_diff = np.round(np.divide(np.sum(np.stack([shortest_paths_build,
                                                            -dijkstra_paths_user]),
                                                  axis=0), shortest_paths_build), 2)

        # forming the user path increase dataframe
        non_nan_idx = ~np.isnan(paths_diff)
        state_pairs = np.argwhere(non_nan_idx)
        state_pairs_from = state_pairs[:, 0]
        state_pairs_to = state_pairs[:, 1]
        state_pairs_diffs = list(paths_diff[non_nan_idx])
        dijkstra_pairs_diff = list(dijkstra_diff[non_nan_idx])
        paths_df = pd.DataFrame({
            'idx_from': state_pairs_from,
            'idx_to': state_pairs_to,
            'path_incr': state_pairs_diffs,
            'dijkstra_diff': dijkstra_pairs_diff
        })
        paths_df = paths_df.sort_values(by=['path_incr', 'dijkstra_diff'],
                                        ascending=False)

        # Tracking metrics to ouput and saving them to self.report_data
        metrics = dict()
        metrics["avg_path_len_incr"] = round(paths_df.path_incr.mean(), 2)
        metrics["avg_path_dijkstra_diff"] = round(paths_df.dijkstra_diff.mean(),2)
        self.report_data["network_metrics"][user].update(metrics)

        # Saving paths dataframe
        df_fname = f"{user}_{self._paths_df_fname}"
        df_fpath = os.path.join(self.output_path, df_fname)
        paths_df.to_csv(df_fpath, index=False)

        # Formatting lines to print to the report
        print_lines.append(f"\nAverage path length increase compared to "
                           f"BuildUser: **{metrics['avg_path_len_incr']}**\n")
        print_lines.append(f"\nAverage Dijkstra difference between shortest "
                           f"paths compared to BuildUser: "
                           f"**{metrics['avg_path_dijkstra_diff']}**\n")
        if len(paths_df.index) > 10:
            print_lines.append(f"**First 10 rows of paths dataframe** for "
                               f"{user}:\n")
            print_lines.append(tabulate(paths_df.head(10), tablefmt="pipe",
                                        headers="keys", showindex=False))
        else:
            print_lines.append(f"**Full paths dataframe** for {user}:\n")
            print_lines.append(tabulate(paths_df, tablefmt="pipe",
                                        headers="keys", showindex=False))
        print_lines.append(f"**NOTE:** The full paths csv is also stored here: "
                           f"`{df_fpath}`")

        return print_lines, paths_df

    # --
    # Private methods to format analyzed sections of the report.
    #   May be overridden.
    #

    def _analyze_crawl_user(self, user):
        """Prepares lines to write to the report for all sections for a given
        crawl user.

        Args:
            user: str denoting a crawl user

        Returns:
            print_lines: list of lines to print to the report
        """
        print_lines = list()

        print_lines.append(f'\n## <a name="{user.lower()}"></a> {user}')

        # record the metrics
        print_lines += self._calculate_user_metrics(user)

        # record the path analysis
        analyze_paths_print_lines, _ = self._analyze_user_paths(user)
        print_lines += analyze_paths_print_lines

        return print_lines

    def _analyze_build(self):
        """Prepares lines to write to the report for all sections for the build
        user.

        Returns:
            print_lines: list of lines to print to the report
        """
        print_lines = list()

        # No sections are coded for the build in BaseAnalyzer.

        return print_lines

    # --
    # Main function that analyzes graph and output results.
    #   Should not need to be overridden.
    #

    def analyze(self):
        """Analyzes graph based on users and sections. Writes a report and
        analyzed .gml file to an output directory at self.output_path.

        """

        # format the top sections
        users = self.users["crawl_users"].keys()
        print_lines = []
        print_lines += self._format_contents(users)
        print_lines += self._format_guide()

        # perform analysis for the build user
        print_lines += self._analyze_build()

        # perform analysis for the crawl_users
        for user in users:
            print_lines += self._analyze_crawl_user(user)

        # write report to file
        report_fpath = pathlib.Path(self.output_path) / self._report_fname
        with open(report_fpath, 'w') as report_file:
            for line in print_lines:
                report_file.write(line)
                report_file.write('\n')

        # write new gml (G) to file
        self._to_gml()

        # write analyzed data to json file
        json_fpath = pathlib.Path(self.output_path) / self._json_data_fname
        dictionary = self.report_data
        self._to_json(json_fpath, dictionary)

    # --
    # Private utility functions.
    #   Should not need to be overridden.
    #

    def _get_user_dict(self, user_model):
        """Helper function to initialize all data required for a user to perform
        analysis

        Args:
            user_model: users.UserModel object

        Returns:
            user_dict: dictionary with keys "user_model" and "graph"
        """

        user_dict = dict()
        user_dict["user_model"] = user_model
        selected_edges = [(u, v, k) for u, v, k, d in
                          self.full_graph.edges(data=True, keys=True)
                          if d[user_model.get_name()] > 0]
        user_model_graph = self.full_graph.edge_subgraph(selected_edges).copy()

        if not user_model_graph.has_node(0):
            user_model_graph.add_nodes_from(self.full_graph.nodes(data=True))
            user_model_graph.remove_nodes_from(list(user_model_graph.nodes())[1:])

        user_dict["graph"] = user_model_graph

        return user_dict

    def _format_contents(self, users):
        """Prepares lines to write to the table of contents section

        Args:
            users: list of str name of the crawl_users to analyze

        Returns:
            print_lines: list of lines to print to the report
        """
        print_lines = list()

        print_lines.append('# Analysis Report')
        print_lines.append('## Contents')

        # --
        # Printing the linkable guide
        #

        print_lines.append(f'* [Guide](#guide)')

        # Printing build_sections links for the guide
        for section in self._build_sections.keys():
            label = self._build_sections[section]["label"]
            print_lines.append(f'    * [{label}](#guide-{section})')

        # Printing crawl_user_sections links for the guide
        for section in self._crawl_user_sections.keys():
            label = self._crawl_user_sections[section]["label"]
            print_lines.append(f'    * [{label}](#guide-{section})')

        # --
        # Printing the linkable build and crawl_user sections
        #

        # Printing build_sections links for the guide
        for section in self._build_sections.keys():
            label = self._build_sections[section]["label"]
            print_lines.append(f'* [{label}](#{section})')

        # Printing crawl_user_sections links for each user
        for user in users:
            print_lines.append(f'* [{user}](#{user.lower()})')
            for section in self._crawl_user_sections.keys():
                label = self._crawl_user_sections[section]["label"]
                print_lines.append(f'    * [{label}](#{user.lower()}-{section})')

        print_lines.append('')

        return print_lines

    def _format_guide(self):
        """Prepares lines to write to guide section

        Returns:
            print_lines: list of lines to print to the report
        """
        print_lines = list()

        print_lines.append(f'## <a name="guide"></a> Guide')

        # Formatting guide for the build_sections
        for section in self._build_sections.keys():
            # Print guide header
            label = self._build_sections[section]["label"]
            print_lines.append(f'\n### <a name="guide-{section}"></a> {label}')

            # Print guide lines
            print_lines += self._build_sections[section]["guide_lines"]

        # Formatting guide for the crawl_user_sections
        for section in self._crawl_user_sections.keys():
            # Print guide header
            label = self._crawl_user_sections[section]["label"]
            print_lines.append(f'\n### <a name="guide-{section}"></a> {label}')

            # Print guide lines
            print_lines += self._crawl_user_sections[section]["guide_lines"]

        return print_lines

    def _to_gml(self):
        """Save a networkx graph, G, to a gml file.

        Normally, we should use nx.write_gml(G, output_fpath), but this does not
        allow custom field names to be written to a file, specifically those with an
        underscore. Also note that this function is very similar to Graph.to_gml(),
        but it iterates over a networkx.Graph function instead of the states and
        edges objects.

        Returns:
            True if there were no errors
        """

        build_user = str(self.users["build_user"]["user_model"])
        gml_fpath = pathlib.Path(self.output_path) / self._analyzed_gml_fname

        try:
            with open(gml_fpath, 'w') as f:
                # Write header information
                f.write('graph [\n')
                f.write('  directed 1\n')
                f.write('  multigraph 1\n')
                f.write(f'  buildUser "{build_user}"\n')

                # Write node data
                for state_id, state in self.full_graph.nodes(data=True):
                    f.write('  node [\n')
                    f.write('    id ' + str(state_id) + '\n')
                    f.write('    label "' + str(state_id) + '"\n')
                    for k, v in state.items():
                        clean_k, clean_v = Graph._clean_kv(k, v)
                        f.write(f'    {clean_k} {clean_v}\n')
                    f.write('  ]\n')

                # Write edge data
                for source, target, edge in self.full_graph.edges(data=True):
                    f.write('  edge [\n')
                    f.write('    source ' + str(source) + '\n')
                    f.write('    target ' + str(target) + '\n')
                    for k, v in edge.items():
                        clean_k, clean_v = Graph._clean_kv(k, v)
                        f.write(f'    {clean_k} {clean_v}\n')
                    f.write('  ]\n')
                f.write(']')
            return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def _to_json(fpath, dictionary):
        """Write dictionary to a filepath with an indent and error check.

        Returns:
            True if there were no errors
        """

        try:
            with open(fpath, 'w') as fp:
                json.dump(dictionary, fp, indent=2)
            return True
        except Exception as e:
            print(e)
            return False
    # --
    # Public utility functions.
    #   May be overridden.
    #

    def plot_graphs(self):
        """Plotting the full graph and the graph of each crawl_user"""
        print("Full graph:")
        nx.draw(self.full_graph, pos=graphviz_layout(self.full_graph),
                with_labels=True)
        plt.show()

        for user in self.users["crawl_users"].keys():
            print(f"{user}'s graph:")
            nx.draw(self.users["crawl_users"][user]["graph"],
                    pos=graphviz_layout(self.full_graph), with_labels=True)
            plt.show()
