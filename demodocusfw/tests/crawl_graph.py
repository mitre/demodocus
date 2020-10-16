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
import os
from sys import stdout
import unittest

import networkx as nx

from .config import mode_crawler_single as config
from demodocusfw.web.server import ThreadedHTTPServer
from demodocusfw.comparator import Comparer
from demodocusfw.controller import Controller
from demodocusfw.utils import set_up_logging
from demodocusfw.web.accessibility.user import VizMouseKeyUser
from demodocusfw.web.user import OmniUser
from demodocusfw.web.web_access import ChromeWebAccess


class TestCrawlGraph(unittest.TestCase):

    url_template = 'http://{}:{}/demodocusfw/tests/sandbox/{}/example.html'

    @classmethod
    def setUpClass(cls):
        set_up_logging(logging.INFO)
        cls._server = ThreadedHTTPServer('localhost', 0)
        cls.server_ip, cls.server_port = cls._server.server.server_address
        print('server_ip: {}'.format(cls.server_ip))
        print('server_port: {}'.format(cls.server_port))
        cls._server.start()
        Comparer.default_pipeline = config.COMPARE_PIPELINE

    @classmethod
    def tearDownClass(cls):
        cls._server.stop()

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()
        self.controller = Controller(ChromeWebAccess, config)

    def tearDown(self):
        config.OUTPUT_DIR.cleanup()
        self.controller.stop()

    def format_url(self, path):
        return self.url_template.format(self.server_ip, self.server_port, path)

    def _test_short_list_accessible_2_paths(self, g, min_id, user):
        """Helper function for asserts with the short URL version of
        test_list_accessible_2_paths().

        There should only be 4 total states in this graph"""
        s0 = g.find_state_by_id(0 + min_id)
        s1 = g.find_state_by_id(1 + min_id)
        s2 = g.find_state_by_id(2 + min_id)
        s3 = g.find_state_by_id(3 + min_id)

        self.assertEqual(6, len(g.get_edges_for_state(s0, user=user)))

        self.assertEqual(1, len(g.path(s0, s1, user)))
        self.assertEqual(1, len(g.path(s1, s0, user)))
        self.assertEqual(2, len(g.path(s0, s3, user)))
        self.assertEqual(2, len(g.path(s3, s0, user)))
        self.assertEqual(2, len(g.path(s1, s2, user)))
        self.assertEqual(2, len(g.path(s2, s1, user)))

    def _test_extended_list_accessible_2_paths(self, g, min_id, user):
        """Helper function for asserts with the short URL version of
        test_list_accessible_2_paths().

        There should be 16 total states in this graph"""

        s0 = g.find_state_by_id(0 + min_id)
        s3 = g.find_state_by_id(3 + min_id)
        s5 = g.find_state_by_id(5 + min_id)
        s7 = g.find_state_by_id(7 + min_id)
        s13 = g.find_state_by_id(13 + min_id)
        s15 = g.find_state_by_id(15 + min_id)

        self.assertEqual(12, len(g.get_edges_for_state(s0, user=user)))

        self.assertEqual(1, len(g.path(s0, s3, user)))
        self.assertEqual(1, len(g.path(s3, s0, user)))
        self.assertEqual(2, len(g.path(s0, s5, user)))
        self.assertEqual(2, len(g.path(s5, s0, user)))
        self.assertEqual(2, len(g.path(s5, s7, user)))
        self.assertEqual(2, len(g.path(s7, s5, user)))
        self.assertEqual(3, len(g.path(s0, s13, user)))
        self.assertEqual(3, len(g.path(s13, s0, user)))
        self.assertEqual(4, len(g.path(s0, s15, user)))
        self.assertEqual(4, len(g.path(s15, s0, user)))
        self.assertEqual(3, len(g.path(s3, s15, user)))
        self.assertEqual(3, len(g.path(s15, s3, user)))

    def test_list_accessible_2(self):
        """Can we find paths between arbitrary states?"""
        if os.environ.get('DEM_RUN_EXTENDED') == 'True':
            url = self.format_url('list/accessible_2')
        else:
            url = self.format_url('test/list_accessible_2')

        self.controller.access.load(url)
        self.assertTrue('Accessible List' in self.controller.access._driver.title)
        user = OmniUser
        g = self.controller.build_graph(user)

        # check status of states
        if os.environ.get('DEM_RUN_EXTENDED') == 'True':
            self.assertEqual(len(g.states), 16)
            self.assertEquals(len(g.edges), 16)
            edges = g.get_edges()
            self.assertEquals(len(edges), 192)
            e = edges[0]
            self.assertTrue(e.supports_user(user.get_name()))
        else:
            self.assertEqual(len(g.states), 4)
            for s in list(g.states):
                self.assertEqual(url, s.data.url)
                self.assertTrue(s.supports_user(user.get_name()))
                self.assertIn(user.get_name(), s.user_paths)
            s1, s2, s3, s4 = list(g.states)
            self.assertNotEqual(s1.data.dom, s2.data.dom)
            self.assertNotEqual(s1.data.dom, s3.data.dom)
            self.assertNotEqual(s1.data.dom, s4.data.dom)
            self.assertNotEqual(s2.data.dom, s3.data.dom)
            self.assertNotEqual(s2.data.dom, s4.data.dom)
            self.assertNotEqual(s3.data.dom, s4.data.dom)

            # check status of edges
            self.assertEqual(len(g.edges), 4)  # 4 entries (the "submitted" state has no outgoing edges)
            edges = g.get_edges()
            e = edges[0]  # Shouldn't really assume anything about this edge other than supported user.
            self.assertTrue(e.supports_user(user.get_name()))

        # Note: states might not be numbered from 0, so get the min id and
        # recalc based on it
        min_id = sorted(g.get_states(), key=lambda s: s.id)[0].id
        # Assumes crawling in deterministic order, consistent state ids
        # relative to the graph
        if os.environ.get('DEM_RUN_EXTENDED') == 'True':
            self._test_extended_list_accessible_2_paths(g, min_id, user)
        else:
            self._test_short_list_accessible_2_paths(g, min_id, user)

        # Ensure gml file is written and has expected values
        gml_filename = '{}.gml'.format(self._testMethodName)
        # Repeat w/ and w/o user name in to_gml() to test fix for #20
        g.to_gml(OmniUser, gml_filename)
        nxg = nx.read_gml(gml_filename)
        self.assertEqual(len(g.states), len(nxg.nodes))
        # count by hand so we can compare w/get_edges()
        edge_count = 0
        for state, edge_set in g.edges.items():
            for edge in edge_set:
                self.assertIn((edge.state1.id, edge.state2.id), nxg.edges)
                edge_count += 1
        self.assertEqual(edge_count, len(nxg.edges))
        self.assertEqual(len(g.get_edges()), len(nxg.edges))
        os.remove(gml_filename)

    def test_list_partaccessible_1_crawl_new_controller(self):
        """Crawl a built graph with a different controller."""
        if os.environ.get('DEM_RUN_EXTENDED') == 'True':
            url = self.format_url('list/partaccessible_1')
        else:
            url = self.format_url('test/list_partaccessible_1')
        self.controller.load(url)
        ouser = OmniUser
        g = self.controller.build_graph(user=ouser)
        nuser = VizMouseKeyUser
        controller2 = Controller(ChromeWebAccess, config)
        controller2.build_user = ouser
        controller2.load(url)
        controller2.crawl_graph(user=nuser, graph=g)

    def test_stub_state(self):
        """Do we capture a stub state when crawling a site with a link to a
        different URL? And does this output properly to the gml file?"""
        url = self.format_url('test/stub_state')
        self.controller.access.load(url)
        user = OmniUser
        g = self.controller.build_graph(user)
        # TODO: switch to tempfile.mkstemp() or equivalent
        gml_filename = '{}.gml'.format(self._testMethodName)
        # Repeat w/ and w/o user name in to_gml() to test fix for #20
        g.to_gml(OmniUser, gml_filename)
        nxg = nx.read_gml(gml_filename)

        # Counting number of stub states in graph object
        g_num_stubs = sum([s.stub for s in g.get_states()])
        self.assertEqual(g_num_stubs, 1)

        # Counting number of stub states in gml file
        nxg_num_stubs = sum([1 for stub in nxg.nodes(data='stub')
                             if stub[1] == "True"])
        self.assertEqual(nxg_num_stubs, 1)

        # Assert other graph/gml equivalencies
        self.assertEqual(len(g.states), len(nxg.nodes))
        # count by hand so we can compare w/get_edges()
        edge_count = 0
        for state, edge_set in g.edges.items():
            for edge in edge_set:
                self.assertIn((edge.state1.id, edge.state2.id), nxg.edges)
                edge_count += 1
        self.assertEqual(edge_count, len(nxg.edges))
        self.assertEqual(len(g.get_edges()), len(nxg.edges))
        os.remove(gml_filename)


if __name__ == '__main__':
    unittest.main()
