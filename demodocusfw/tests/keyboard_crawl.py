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

from sys import stdout
import unittest

from .config import mode_test as config
from demodocusfw.web.server import ThreadedHTTPServer
from demodocusfw.controller import Controller
from demodocusfw.utils import DemodocusTemporaryDirectory
from demodocusfw.web.user import OmniUser
from demodocusfw.web.web_access import ChromeWebAccess


class TestKeyboardCrawl(unittest.TestCase):

    url_template = 'http://{}:{}/demodocusfw/tests/sandbox/test/event_unit_tests/{}.html'

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
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()
        config.MULTI = False
        config.NUM_THREADS = 1
        config.OUTPUT_DIR = DemodocusTemporaryDirectory()
        self.controller = Controller(ChromeWebAccess, config)

    def tearDown(self):
        config.OUTPUT_DIR.cleanup()
        self.controller.stop()

    def format_url(self, path):
        return self.url_template.format(self.server_ip, self.server_port, path)

    def crawl(self, path):
        """Testing the basics of crawl graph result."""
        url = self.format_url(path)
        self.controller.access.load(url)
        user = OmniUser
        g = self.controller.build_graph(user)

        # check status of states
        self.assertEqual(len(g.states), 2)
        for s in list(g.states):
            self.assertEqual(url, s.data.url)
            self.assertTrue(s.supports_user(user.get_name()))
            self.assertIn(user.get_name(), s.user_paths)
        s1, s2 = list(g.states)
        self.assertNotEqual(s1.data.dom, s2.data.dom)

        # check status of edges
        self.assertEqual(len(g.edges), 1)
        edges = g.get_edges()
        e = edges[0]
        self.assertIn(user.get_name(), e.get_user_names())
        self.assertEqual(s1, e.state1)
        self.assertEqual(s2, e.state2)
        self.assertEqual('/html/body/button', str(e.element))
        self.assertTrue('key_press' in str(e.action))
        self.assertTrue(e.supports_user(user.get_name()))
        # Verify that rewind is working; should find all six events on all
        # four tests.
        for event_type in ['ArrowDown', 'ArrowLeft', 'ArrowRight',
            'ArrowUp', 'Enter', 'Space']:
            found_event = False
            # print('Looking for event {}'.format(event_type))
            for e in edges:
                # print('...comparing to {} event'.format(e.action))
                if event_type in str(e.action):
                    # print(' -> found event {}'.format(event_type))
                    found_event = True
                    break
            self.assertTrue(found_event)

    def test_code(self):
        self.crawl('code')

    def test_key(self):
        self.crawl('key')

    def test_keyCode(self):
        self.crawl('keyCode')

    def test_which(self):
        self.crawl('which')


if __name__ == '__main__':
    unittest.main()
