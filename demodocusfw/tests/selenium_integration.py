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
from demodocusfw.controller import Controller
from demodocusfw.utils import DemodocusTemporaryDirectory
from demodocusfw.web.web_access import ChromeWebAccess
from demodocusfw.web.server import ThreadedHTTPServer


class TestSeleniumIntegration(unittest.TestCase):

    default_url = 'https://www.mitre.org/'

    url_template = 'http://{}:{}/demodocusfw/tests/sandbox/test/{}/example.html'

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

    def format_url(self, path):
        return self.url_template.format(self.server_ip, self.server_port, path)

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()
        config.MULTI = False
        config.NUM_THREADS = 1
        config.OUTPUT_DIR = DemodocusTemporaryDirectory()
        self.controller = Controller(ChromeWebAccess, config)

    def tearDown(self):
        self.controller.stop()
        config.OUTPUT_DIR.cleanup()

    def test_controller_page_load(self):
        self.controller.access.load('http://www.google.com')
        self.assertTrue('Google' in self.controller.access._driver.title)

    def test_query_lxml_xpath(self):
        # Remember relative paths are converted to absolute.
        xpath = '//li[contains(@tabindex, "0")]'
        self.controller.access.load(self.format_url("list_accessible_2"))
        r = self.controller.access.query_xpath(xpath, find_one=True)
        self.assertEqual('Eggs', self.controller.access.get_lxml_element(r).text.strip())

    def test_query_selenium_xpath(self):
        xpath = '//li[contains(@tabindex, "0")]'
        self.controller.access.load(self.format_url("list_accessible_2"))
        r = self.controller.access.query_xpath(xpath, find_one=True)
        self.assertEqual('Eggs', self.controller.access.get_selenium_element(r).text.strip())

    def test_get_url(self):
        self.controller.access.load(self.default_url)
        self.assertEqual(self.default_url,
            self.controller.access.get_state_data().url)

    def test_get_xpath(self):
        about_xpath = '//li[contains(@tabindex, "0")]'
        expected_xpath = '/html/body/ul/li[1]'
        self.controller.access.load(self.format_url("list_accessible_2"))
        r = self.controller.access.query_xpath(about_xpath, find_one=True)
        self.assertEqual(expected_xpath, r.xpath)


if __name__ == '__main__':
    unittest.main()
