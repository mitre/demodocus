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

import json
import os
from pathlib import Path
import subprocess
import sys
from sys import stdout
import unittest

from demodocusfw.web.server import ThreadedHTTPServer
from demodocusfw.crawler import import_config_from_spec, check_config_mode
from demodocusfw.utils import DemodocusTemporaryDirectory
from demodocusfw.web.accessibility.user import VizKeyUser
from demodocusfw.web.analysis import WebAccessAnalyzer


class TestAnalysis(unittest.TestCase):
    url_template = 'http://{}:{}/demodocusfw/tests/sandbox/{}/example.html'

    @classmethod
    def setUpClass(cls):
        cls._server = ThreadedHTTPServer('localhost', 0)
        cls.server_ip, cls.server_port = cls._server.server.server_address
        print('server_ip: {}'.format(cls.server_ip))
        print('server_port: {}'.format(cls.server_port))
        cls._server.start()

    @classmethod
    def tearDownClass(cls):
        cls._server.stop()

    def setUp(self):
        self.run_extended = False
        if os.environ.get('DEM_RUN_EXTENDED') == 'True':
            self.run_extended = True

        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()
        # Note: instantiate afresh each time we run, not just once w/static val
        self.output_dir = DemodocusTemporaryDirectory()

    def tearDown(self):
        # Remove temp dir
        self.output_dir.cleanup()

    def format_url(self, path):
        return self.url_template.format(self.server_ip, self.server_port, path)

    def _test_analysis(self, example_str, test_func):
        pyexe = sys.executable
        """Crawl with each controller type and a variety of thread counts.
        Verify their output is all the same, or at least graph-isomorphic.
        This code repeats itself a lot. Seemed best to be explicit at first."""
        crawl_dir = Path(self.output_dir.name)
        url = self.format_url(example_str)
        base_args = [
            pyexe,
            (Path('.') / 'crawler.py').absolute(),
            '--output_dir',
            crawl_dir,
            '--mode',
            # TODO update to a reduced crawl
            'demodocusfw.tests.config.mode_crawler_single',
            url]

        # Multi-threaded, 4 threads
        c4_path = crawl_dir / 'multi4'
        c4_args = base_args[:]
        c4_args[3] = c4_path
        c4_args[5] = 'demodocusfw.tests.config.mode_crawler_multi4'
        c4_args = [str(a) for a in c4_args]
        print('Four threads')
        c4_p = subprocess.run(c4_args)
        self.assertEqual(c4_p.returncode, 0)

        gml_fpath = c4_path / 'full_graph.gml'

        # loading in analyzer used in the crawl
        config_spec = check_config_mode(c4_args[5])
        config = import_config_from_spec(config_spec)
        analyzer = config.ANALYZER_CLASS(gml_fpath, config)
        analyzer._analyze_build()

        # Testing results that are different for extended vs short crawls
        test_func(analyzer)

        # Asserting that the actions captured in the graph are consistent with
        #  the user model
        user = "VizKeyUser"
        keyboard_actions_graph = analyzer._get_user_actions_subgraph(user)
        actions = {str(e) for e in VizKeyUser.actions}
        graph_actions = {i[2]['action'] for i in
                         keyboard_actions_graph.edges(data=True)}
        self.assertTrue(all([a in actions for a in graph_actions]))

        # Ensuring that the expected files are outputted
        files_outputted = os.listdir(c4_path)
        self.assertTrue(analyzer._analyzed_gml_fname in files_outputted)
        self.assertTrue(analyzer._json_data_fname in files_outputted)
        self.assertTrue(analyzer._report_fname in files_outputted)
        self.assertTrue("network_layouts" in files_outputted)
        self.assertTrue("VizKeyUser_paths_df.csv" in files_outputted)
        self.assertTrue("VizMouseKeyUser_paths_df.csv" in files_outputted)

        # Make sure the x,y fields are included in the full graph
        pos_fiels = {'x_fr_0', 'x_fr_2', 'x_fr_4', 'x_fr_6', 'x_fr_8',
                     'x_kk_0', 'x_kk_2', 'x_kk_4', 'x_kk_6', 'x_kk_8',
                     'y_fr_0', 'y_fr_2', 'y_fr_4', 'y_fr_6', 'y_fr_8',
                     'y_kk_0', 'y_kk_2', 'y_kk_4', 'y_kk_6', 'y_kk_8'}
        for _, node_dict in list(analyzer.full_graph.nodes(data=True)):
            assert pos_fiels.issubset(set(node_dict.keys()))

        # Try to open the json file. If it didn't write correctly, it ALMOST
        #  certainly will not open correctly.
        try:
            with open(c4_path / analyzer._json_data_fname) as json_file:
                analyzed_results = json.load(json_file)
            no_loading_error = True
            # Make sure we have top-level sections correct.
            self.assertTrue(['els_states', 'network_metrics', 'accessibility'] ==
                            list(analyzed_results.keys()))
        except:
            no_loading_error = False

        # Couldn't properly load the analyzed json results in
        self.assertTrue(no_loading_error)

    def _test_extended_analysis(self, analyzer):
        # asserting number of nodes for Omni graph and Keyboard graph
        full_graph = analyzer.full_graph
        user = "VizKeyUser"
        analyzer._analyze_crawl_user(user)
        keyboard_graph = analyzer.users["crawl_users"][user]["graph"]
        keyboard_actions_graph = analyzer._get_user_actions_subgraph(user)
        self.assertEqual(len(full_graph.nodes()), 16)
        self.assertEqual(len(full_graph.edges()), 160)
        self.assertEqual(len(keyboard_graph.nodes()), 8)
        self.assertEqual(len(keyboard_graph.edges()), 48)

        # asserting the paths analysis is working
        _, paths_df = analyzer._analyze_user_paths(user)
        self.assertEqual(round(paths_df['path_incr'].mean(), 5), 0.0000)
        self.assertEqual(paths_df.shape, (56, 4))

        # asserting that inaccessible improvements are found
        keyboard_node_ids = list(keyboard_graph.nodes())
        user_inaccessible_graph = analyzer._get_inaccessible_graph(user)
        inaccessible_node_ids = list(user_inaccessible_graph.nodes())
        potential_improvements = analyzer._find_all_accessible(
            keyboard_node_ids,
            inaccessible_node_ids,
            keyboard_actions_graph)

        # Commenting this out -- It isn't guaranteed to be node 4.
        # self.assertEqual(len(potential_improvements[4]['new_states_included']), 7)
        elements_dict, _ = analyzer._elements_to_fix(potential_improvements,
                                                     user)
        self.assertTrue('/html/body/ul/li[4]' in elements_dict)

    def _test_short_analysis(self, analyzer):
        # asserting number of nodes for Omni graph and Keyboard graph
        full_graph = analyzer.full_graph
        user = "VizKeyUser"
        analyzer._analyze_crawl_user(user)
        keyboard_graph = analyzer.users["crawl_users"][user]["graph"]
        keyboard_actions_graph = analyzer._get_user_actions_subgraph(user)
        self.assertEqual(len(full_graph.nodes()), 4)
        self.assertEqual(len(full_graph.edges()), 16)
        self.assertEqual(len(keyboard_graph.nodes()), 2)
        self.assertEqual(len(keyboard_graph.edges()), 4)

        # asserting the paths analysis is working
        _, paths_df = analyzer._analyze_user_paths(user)
        self.assertEqual(round(paths_df['path_incr'].mean(), 5), 0.0000)
        self.assertEqual(paths_df.shape, (2, 4))

        # asserting that inaccessible improvements are found
        keyboard_node_ids = list(keyboard_graph.nodes())
        user_inaccessible_graph = analyzer._get_inaccessible_graph(user)
        inaccessible_node_ids = list(user_inaccessible_graph.nodes())
        potential_improvements = analyzer._find_all_accessible(
            keyboard_node_ids,
            inaccessible_node_ids,
            keyboard_actions_graph)

        # Commenting this out -- It isn't guaranteed to be node 4.
        # self.assertEqual(len(potential_improvements[4]['new_states_included']), 7)
        elements_dict, _ = analyzer._elements_to_fix(potential_improvements,
                                                     user)
        self.assertTrue('/html/body/ul/li[2]' in elements_dict)

        # Make sure the results stored in element_map.json are correct
        with open(Path(analyzer.output_path) / "element_map.json") as json_file:
            element_map = json.load(json_file)

        # Make sure that the number violations tracked is as expected
        state_0_violations = element_map["0"]["violations"]
        self.assertEqual(len(state_0_violations), 2)
        for violation in state_0_violations:
            self.assertEqual(violation["type"], "composite")
        self.assertEqual(len(element_map["1"]["violations"]), 1)
        self.assertEqual(len(element_map["2"]["violations"]), 1)
        self.assertEqual(len(element_map["3"]["violations"]), 0)

        # Manually check violation on state 1
        expected_v1 = {'type': 'atomic',
                       'level': 'warning',
                       'category': 'S.C. 2.5.5',
                       'element': {'x': 48,
                                   'y': 104,
                                   'width': 1864,
                                   'height': 18,
                                   'xpath': '/html/body/ul/li[2]',
                                   'text': 'Sugar',
                                   'tag': 'li'},
                       'group_id': 0
                      }
        violation_1 = element_map["1"]["violations"][0]
        violation_1.pop("code")
        violation_1.pop("replay")

        # Manually check violation on state 2
        expected_v2 = {'type': 'atomic',
                       'level': 'warning',
                       'category': 'S.C. 2.5.5',
                       'element': {'x': 48,
                                   'y': 50,
                                   'width': 1864,
                                   'height': 18,
                                   'xpath': '/html/body/ul/li[1]',
                                   'text': 'Eggs',
                                   'tag': 'li'},
                       'group_id': 0
                       }
        violation_2 = element_map["2"]["violations"][0]
        violation_2.pop("code")
        violation_2.pop("replay")

        # Ordering is sometimes varied, make sure that they both exist
        if violation_1["element"]["text"] == "Sugar":
            self.assertEqual(violation_1, expected_v1)
            self.assertEqual(violation_2, expected_v2)
        else:
            self.assertEqual(violation_1, expected_v2)
            self.assertEqual(violation_2, expected_v1)

    def test_analysis(self):
        if self.run_extended:
            self._test_analysis('list/partaccessible_1', self._test_extended_analysis)
        else:
            self._test_analysis('test/list_partaccessible_1', self._test_short_analysis)

    def test_parse_color_string(self):
        """ Tests parse color string returns correct lists """
        rgb_simple = "rgb(1, 2, 3)"
        rgba_simple = "rgba(1, 2, 3, 0.7)"
        rgb_border = "1px solid rgb(255, 123, 2)"
        rgba_border = "1px solid rgba(32, 12, 133, 0.3)"
        none = "1px solid"

        self.assertEqual([1, 2, 3], WebAccessAnalyzer.parse_color_string(rgb_simple))
        self.assertEqual([1, 2, 3, 0.7], WebAccessAnalyzer.parse_color_string(rgba_simple))
        self.assertEqual([255, 123, 2], WebAccessAnalyzer.parse_color_string(rgb_border))
        self.assertEqual([32, 12, 133, 0.3], WebAccessAnalyzer.parse_color_string(rgba_border))
        self.assertEqual(None, WebAccessAnalyzer.parse_color_string(none))

    def test_order_is_valid(self):
        """ Test order is valid """
        # 'Elements' Mapped on 100 by 100 page
        top_left = {"position": {"x": 0, "y": 0}}
        top_right = {"position": {"x": 100, "y": 20}}
        middle = {"position": {"x": 50, "y": 50}}
        bottom_left = {"position": {"x": 10, "y": 75}}
        bottom_right = {"position": {"x": 80, "y": 80}}

        # 'Regular' ordering
        self.assertTrue(WebAccessAnalyzer.order_is_valid(top_left, top_right))
        self.assertTrue(WebAccessAnalyzer.order_is_valid(top_right, middle))
        self.assertTrue(WebAccessAnalyzer.order_is_valid(middle, bottom_left))
        self.assertTrue(WebAccessAnalyzer.order_is_valid(bottom_left, bottom_right))

        # Follow our rules
        self.assertTrue(WebAccessAnalyzer.order_is_valid(middle, top_right))
        self.assertTrue(WebAccessAnalyzer.order_is_valid(bottom_left, middle))

        # Breaks our rules
        self.assertFalse(WebAccessAnalyzer.order_is_valid(top_right, top_left))
        self.assertFalse(WebAccessAnalyzer.order_is_valid(middle, top_left))
        self.assertFalse(WebAccessAnalyzer.order_is_valid(bottom_right, middle))
        self.assertFalse(WebAccessAnalyzer.order_is_valid(bottom_right, bottom_left))
        
    def test_border_is_visible(self):
        """ Test border would show as visible in browser """
        empty = ""
        hidden = "0px solid rgb(123, 12, 1)"
        hidden2 = "1px none rgb(123, 12, 1)"
        visible = "1px solid rgb(123, 12, 1)"

        self.assertFalse(WebAccessAnalyzer.border_is_visible(empty))
        self.assertFalse(WebAccessAnalyzer.border_is_visible(hidden))
        self.assertFalse(WebAccessAnalyzer.border_is_visible(hidden2))
        self.assertTrue(WebAccessAnalyzer.border_is_visible(visible))

    def test_border_is_sufficient(self):
        """ Tests that border has changed sufficiently """
        visible = "1px solid "
        invisible = "0px solid "
        light = "rgb(252, 230, 16)" # Yellow >10:1 contrast with black, <1.5:1 with white
        dark = "rgb(31, 22, 49)" # Dark purple 1.2:1 contrast black to purple
        white = "rgb(255, 255, 255)"
        black = "rgb(0, 0, 0)"

        # border_is_sufficient(before_border, focus_border, other_border, parent_background, min_border_contrast=1.5):
        
        # Focused border not visible
        self.assertFalse(WebAccessAnalyzer.border_is_sufficient(visible + light, invisible + light, "", white))
        # Border invisible before but visible after
        self.assertTrue(WebAccessAnalyzer.border_is_sufficient("", visible + dark, "", white))
        # Border visible before and after, but not enough color change
        self.assertFalse(WebAccessAnalyzer.border_is_sufficient(visible + black, visible + dark, "", white))
        # Border visible before and after, with sufficient change
        self.assertTrue(WebAccessAnalyzer.border_is_sufficient(visible + light, visible + dark, "", white))
        # Other border visible before and not sufficient change
        self.assertFalse(WebAccessAnalyzer.border_is_sufficient("", visible + dark, visible + black, white))
        # Other border visible, but sufficient change
        self.assertTrue(WebAccessAnalyzer.border_is_sufficient("", visible + dark, visible + light, white))
        # Both border and other border visible, not sufficient change compared to other
        self.assertFalse(WebAccessAnalyzer.border_is_sufficient(visible + light, visible + dark, visible + dark, white))
        # Border change, but insufficient with background
        self.assertFalse(WebAccessAnalyzer.border_is_sufficient(visible + light, visible + dark, "", black))


if __name__ == '__main__':
    unittest.main()
