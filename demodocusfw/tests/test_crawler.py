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
from pathlib import Path
import subprocess
import sys
from sys import stdout
import unittest

import networkx as nx
import pandas as pd

from .config import mode_crawler_single as config_single
from demodocusfw.web.server import ThreadedHTTPServer
from demodocusfw.crawler import import_config_from_spec, check_config_mode
from demodocusfw.utils import DemodocusTemporaryDirectory, set_up_logging, ROOT_DIR
from demodocusfw.web.utils import serve_output_folder
from demodocusfw.web.web_access import ChromeWebAccess


class TestCrawler(unittest.TestCase):

    ep_template = 'http://{}:{}/demodocusfw/tests/sandbox/{}/example.html'

    @classmethod
    def setUpClass(cls):
        set_up_logging(logging.INFO)
        # Set up server to serve up the examples.
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
        self.graph_dictionary = dict()

    def tearDown(self):
        # Remove temp dir
        self.output_dir.cleanup()
        self.output_dir = None

    def format_ep(self, path):
        return self.ep_template.format(self.server_ip, self.server_port, path)

    def _run(self, args):
        """Runs a subprocess, prints output and waits for it to exit."""
        # Convert everything to strings.
        args = [str(a) for a in args]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with proc.stdout:
            for line in iter(proc.stdout.readline, b''):
                print(line)
        exitcode = proc.wait(1200)
        print("Exitcode " + str(exitcode))
        self.assertEqual(exitcode, 0)

    def _run_ep(self, ep, out_folder, mode):
        """Runs a subprocess crawler on a single url.

        Args:
            ep: single url to crawl
            out_folder: where to put the output
            mode: the config mode to use, as a string

        Returns:
            full output path
        """
        pyexe = sys.executable
        path = Path(self.output_dir.name) / out_folder
        # Single-thread, original controller
        args = [
            pyexe,
            ROOT_DIR / 'crawler.py',
            '--output_dir',
            path,
            '--mode',
            mode,
            ep]
        self._run(args)
        return path

    def _run_eps(self, eps_file, out_folder, mode):
        """Runs a subprocess crawler on a file with multiple urls.

        Args:
            eps_file: file with urls, each on a line
            out_folder: where to put the output
            mode: the config mode to use, as a string

        Returns:
            full output path
        """
        pyexe = sys.executable
        path = Path(self.output_dir.name) / out_folder
        # Single-thread, original controller
        args = [
            pyexe,
            ROOT_DIR / 'crawler.py',
            '--output_dir',
            path,
            '--mode',
            mode,
            '-i',
            eps_file]
        self._run(args)
        return path

    def _make_eps_file(self, eps):
        """Given a list of urls, creates an input file. Returns full path to file."""
        ep_txt_fpath = Path(self.output_dir.name) / 'eps.txt'
        with open(ep_txt_fpath, 'w') as file:
            for line in eps:
                file.write(line + '\n')
        return ep_txt_fpath

    def _test_equivalence(self, example_str):
        ep = self.format_ep(example_str)
        """Crawl with each controller type and a variety of thread counts.
        Verify their output is all the same, or at least graph-isomorphic.
        This code repeats itself a lot. Seemed best to be explicit at first."""
        # Single-thread, original controller
        c1_path = self._run_ep(ep, 'single', 'demodocusfw.tests.config.mode_crawler_single_w_screenshots')
        # Single thread, multicontroller
        c2_path = self._run_ep(ep, 'multi1', 'demodocusfw.tests.config.mode_crawler_multi1_w_screenshots')
        # Multi-threaded, 4 threads
        c4_path = self._run_ep(ep, 'multi4', 'demodocusfw.tests.config.mode_crawler_multi4_w_screenshots')

        c1_gml = c1_path / 'full_graph.gml'
        c1_nxg = nx.read_gml(c1_gml)

        c2_gml = c2_path / 'full_graph.gml'
        c2_nxg = nx.read_gml(c2_gml)

        c4_gml = c4_path / 'full_graph.gml'
        c4_nxg = nx.read_gml(c4_gml)

        # test isomorphisms
        self.assertTrue(nx.is_isomorphic(c1_nxg, c2_nxg))
        self.assertTrue(nx.is_isomorphic(c1_nxg, c4_nxg))

        # test that click events are fuzzy values for VizMouseKeyUser
        c1norm_clicks = [i[2]["VizMouseKeyUser"] for i in c1_nxg.edges(data=True)
                         if i[2]["action"] == "click"]
        c2norm_clicks = [i[2]["VizMouseKeyUser"] for i in c2_nxg.edges(data=True)
                         if i[2]["action"] == "click"]
        c4norm_clicks = [i[2]["VizMouseKeyUser"] for i in c4_nxg.edges(data=True)
                         if i[2]["action"] == "click"]
        self.assertTrue(min(c1norm_clicks) >= 0 and max(c1norm_clicks) <= 1)
        self.assertTrue(min(c2norm_clicks) >= 0 and max(c2norm_clicks) <= 1)
        self.assertTrue(min(c4norm_clicks) >= 0 and max(c4norm_clicks) <= 1)

        # Ensure other files are outputted as expect
        self._test_output_dir(c1_path)
        self._test_output_dir(c2_path)
        self._test_output_dir(c4_path)

    """
    move out some of the asserts
    find an easier example to test on
    """

    def _run_compile_outputs(self, path, output_csv_fpath):
        """Runs a subprocess call to util_scripts/compile_outputs.py .

        Args:
            path: path of crawl output dirs to run compile_outputs.py for.
            output_csv_fpath: filepath to write csv to
        """
        pyexe = sys.executable
        # Single-thread, original controller
        args = [
            pyexe,
            ROOT_DIR / 'util_scripts' / 'compile_outputs.py',
            Path(path).absolute(),
            "-o",
            Path(output_csv_fpath).absolute()
            ]
        self._run(args)

    def _test_output_dir_helper(self, single_output_path):
        # Check that state files are written
        self.assertTrue((single_output_path / 'states').is_dir())

        # Check that screenshot files are written
        self.assertTrue((single_output_path / 'screenshots').is_dir())

        # Check that the pre-computed network layout files are written
        self.assertTrue((single_output_path / 'network_layouts').is_dir())

        other_expected_files = ['analysis_report.md',
                                'analyzed_data.json',
                                'crawl.log',
                                'crawl_config.txt',
                                'element_map.json']

        for fname in other_expected_files:
            self.assertTrue((single_output_path / fname).is_file())

    def _test_output_dir(self, output_path):
        """Crawl with each controller type and a variety of thread counts.
        Verify their output is all the same, or at least graph-isomorphic.
        This code repeats itself a lot. Seemed best to be explicit at first."""
        files_in_path = os.listdir(str(output_path))

        # If multiple URLs were crawled with one call to demodocus
        if 'ep-0' in files_in_path:
            single_output_paths = [path_name for path_name in files_in_path
                                   if 'ep-' in path_name]

            for i_output_path in single_output_paths:
                # Ensure all output files are written as expected
                self._test_output_dir_helper(output_path / i_output_path)

            # Check that we can compile stats across the mutliple URL results
            compiled_csv_fpath = output_path / 'compiled_stats.csv'
            self._run_compile_outputs(output_path, compiled_csv_fpath)
            self.assertTrue(compiled_csv_fpath.exists())
            compiled_df = pd.read_csv(compiled_csv_fpath)
            # Two rows (since this compiles data over two crawls
            self.assertEqual(compiled_df.shape[0], len(i_output_path))
            # More than 13 columns (13 are generic crawl fields, plus 3 for
            #  each usermodel)
            self.assertTrue(compiled_df.shape[1] > 13)
            # Assert that after the 13 generic columns, there is a multiple of
            #  three columns left
            self.assertEqual((compiled_df.shape[1] - 13) % 3, 0)

        else:
            # Ensure all output files are written as expected
            self._test_output_dir_helper(output_path)

            compiled_csv_fpath = output_path / 'compiled_stats.csv'
            self._run_compile_outputs(output_path, compiled_csv_fpath)
            self.assertTrue(compiled_csv_fpath.exists())
            compiled_df = pd.read_csv(compiled_csv_fpath)
            # 1 row (since this compiles data over just 1 crawl)
            self.assertEqual(compiled_df.shape[0], 1)
            # More than 13 columns (13 are generic crawl fields, plus 3 for
            #  each usermodel)
            self.assertTrue(compiled_df.shape[1] > 13)
            # Assert that after the 13 generic columns, there is a multiple of
            #  three columns left
            self.assertEqual((compiled_df.shape[1] - 13) % 3, 0)

    def _run_perceive(self, example_str, test_func):
        """Crawl with a single controller to verify that the
        perceivability functionality is working properly"""
        ep = self.format_ep(example_str)
        pyexe = sys.executable
        crawl_dir = Path(self.output_dir.name)
        base_args = [
            pyexe,
            ROOT_DIR / 'crawler.py',
            '--output_dir',
            crawl_dir,
            '--mode',
            'demodocusfw.tests.config.mode_crawler_single',
            ep]
        # Single-thread, original controller
        c1_path = crawl_dir / 'single'
        c1_args = base_args[:]
        c1_args[3] = c1_path
        # Convert everything to strings.
        c1_args = [str(a) for a in c1_args]
        c1_p = subprocess.run(c1_args)
        self.assertEqual(c1_p.returncode, 0)

        gml_fpath = c1_path / 'full_graph.gml'

        # loading in analyzer used in the crawl
        config_spec = check_config_mode(c1_args[5])
        config = import_config_from_spec(config_spec)
        analyzer = config.ANALYZER_CLASS(gml_fpath, config)
        user = "VizMouseKeyUser"
        VizMouseKeyUser_graph = analyzer.users["crawl_users"][user]["graph"]
        test_func(analyzer.full_graph, VizMouseKeyUser_graph)

    def _test_short_perceive(self, full_graph, user_graph):
        # Omni user and subuser will access different number of nodes and edges
        # due to color contrast
        # Three nodes: 0, "accessible", "inaccessible"
        self.assertEqual(len(full_graph.nodes()), 3)
        # 8 edges going from 0 to "inaccessible" state.
        # 4 edges going from 0 to "accessible" state.
        # 8 edges going from "accessible" to "inaccessible".
        # 4 edges going from "inaccessible" to "accessible".
        self.assertEqual(len(full_graph.edges()), 24)
        self.assertEqual(len(user_graph.nodes()), 2)
        # Can only use the 4 edges going to the "accessible" state.
        self.assertEqual(len(user_graph.edges()), 4)

        # making sure the perceive functions are working. Sometimes the indexing
        #  doesn't produce the results in the same order, so we are just making
        #  sure both values match
        # Get all the edges going from 0 to the "accessible" state.
        pcv_scores = sorted(list(dict(full_graph[0][2]).values()), key=lambda x: x["VizMouseKeyUser"])
        # This is the easiest way: Clicking button 3.
        self.assertAlmostEqual(pcv_scores[-1]["VizMouseKeyUser"], 0.661, 2)
        # This is the hardest way: Pressing Enter on buttons 3 or 4.
        # (Remember we can tab forward or backward so the distance is equal.)
        self.assertAlmostEqual(pcv_scores[0]["VizMouseKeyUser"], 0.543, 2)

    def _test_extended_perceive(self, full_graph, user_graph):
        # Omni user and subuser will access different number of nodes and edges
        # due to color contrast
        self.assertEqual(len(full_graph.nodes()), 64)
        self.assertEqual(len(full_graph.edges()), 384)
        self.assertEqual(len(user_graph.nodes()), 1)
        self.assertEqual(len(user_graph.edges()), 0)

    def test_list_accessible_3_equivalence(self):
        # Only run this test for extended tests
        if self.run_extended:
            self._test_equivalence('list/accessible_3')

    def test_list_inaccessible_1_equivalence(self):
        if self.run_extended:
            self._test_equivalence('list/inaccessible_1')
        else:
            self._test_equivalence('test/list_inaccessible_1')

    def test_perceivability(self):
        # Only run this test for extended tests
        if self.run_extended:
            self._run_perceive('perceivability_example', self._test_extended_perceive)

    def test_demodocus_nojs(self):
        config_single.OUTPUT_DIR = self.output_dir

        """ Try loading an "additive" javascript page and make sure elements are not duplicated."""
        # Since there's no controller, set up server to serve up the output folder.
        output_server = serve_output_folder(config_single)

        path = 'http://{}:{}/demodocusfw/tests/sandbox/misc/additive_javascript/additive3.html'.format(
            self.server_ip, self.server_port)
        access = ChromeWebAccess(config_single)
        self.assertTrue(access.load(path))
        # There should be only two inputs on the page.
        target_els = access.query_xpath("//input")
        self.assertEqual(len(target_els), 2)

        path = 'http://{}:{}/demodocusfw/tests/sandbox/misc/additive_javascript/additive2.html'.format(
            self.server_ip, self.server_port)
        self.assertTrue(access.load(path))
        # There should be only one jquery reference on the page.
        target_els = access.query_xpath("//script[@src]")
        self.assertEqual(len(target_els), 1)

        access.shutdown()
        output_server.stop()

    def test_page_cookies(self):
        """ Test to determine if we can handle pages that try to set cookies """
        # Since there's no controller, set up server to serve up the output folder.
        config_single.OUTPUT_DIR = self.output_dir
        output_server = serve_output_folder(config_single)
        access = ChromeWebAccess(config_single)
        # Not setting testing mode to true
        access.load(self.format_ep('cookies'))
        self.assertTrue('success' in access._driver.title)
        access.shutdown()
        output_server.stop()


if __name__ == '__main__':
    unittest.main()
