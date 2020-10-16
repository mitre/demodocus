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
from sys import stdout
import unittest

from .config import mode_crawler_single as config
from demodocusfw.web.server import ThreadedHTTPServer
from demodocusfw.comparator import Comparer
from demodocusfw.utils import DemodocusTemporaryDirectory, set_up_logging
from demodocusfw.web.controller import ControllerReduced, \
    MultiControllerReduced
from demodocusfw.web.user import OmniUser
from demodocusfw.web.web_access import ChromeWebAccess


class TestReducedCrawl(unittest.TestCase):

    url_template = 'http://{}:{}/demodocusfw/tests/sandbox/{}/example.html'

    def format_url(self, path):
        return self.url_template.format(self.server_ip, self.server_port, path)

    @classmethod
    def setUpClass(cls):
        cls._server = ThreadedHTTPServer('localhost', 0)
        cls.server_ip, cls.server_port = cls._server.server.server_address
        print('server_ip: {}'.format(cls.server_ip))
        print('server_port: {}'.format(cls.server_port))
        cls._server.start()
        Comparer.default_pipeline = config.COMPARE_PIPELINE

        # Set up logging
        set_up_logging(logging.INFO)

    @classmethod
    def tearDownClass(cls):
        cls._server.stop()

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()
        config.OUTPUT_DIR = DemodocusTemporaryDirectory()

    def tearDown(self):
        config.OUTPUT_DIR.cleanup()

    def test_test_partaccessible_1_crawl(self):
        """Testing the basics of crawl graph result."""

        url = self.format_url('test/list_partaccessible_1')
        controller = ControllerReduced(ChromeWebAccess, config)
        controller.access.load(url)
        g = controller.build_graph(OmniUser)
        controller.stop()

        # check status of states
        self.assertEqual(len(g.states), 3)

    def test_multi_test_partaccessible_1_crawl(self):
        """Testing the basics of crawl graph result."""
        url = self.format_url('test/list_partaccessible_1')
        controller = MultiControllerReduced(ChromeWebAccess, config)
        g = controller.build_graph(OmniUser, entry_point=url)
        controller.stop()

        # check status of states
        self.assertEqual(len(g.states), 3)


if __name__ == '__main__':
    unittest.main()
