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
from demodocusfw.utils import DemodocusTemporaryDirectory, set_up_logging, stop_logging
from demodocusfw.web.web_access import ChromeWebAccess


class TestKeyboardEvaluation(unittest.TestCase):

    ep_template = 'http://{}:{}/demodocusfw/tests/sandbox/{}'

    @classmethod
    def setUpClass(cls):
        # Server for serving up examples.
        cls._server = ThreadedHTTPServer('localhost', 0)
        cls.server_ip, cls.server_port = cls._server.server.server_address
        print('server_ip: {}'.format(cls.server_ip))
        print('server_port: {}'.format(cls.server_port))
        cls._server.start()

        # Set up config.
        config.MULTI = False
        config.NUM_THREADS = 1
        config.HEADLESS = True
        config.OUTPUT_DIR = DemodocusTemporaryDirectory()
        cls.controller = Controller(ChromeWebAccess, config)

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()

    @classmethod
    def tearDownClass(cls):
        stop_logging()
        cls.controller.stop()
        cls._server.stop()
        config.OUTPUT_DIR.cleanup()

    def format_ep(self, path):
        return self.ep_template.format(self.server_ip, self.server_port, path)

    def load_and_get_tabs(self, path):
        self.controller.access.load(self.format_ep(path))
        # generate tab order returns a tuple of (tab_els, selenium elements)
        # We want the tab els since they store all of the data
        return self.controller.access.generate_tab_order()[0]
    
    def test_correct_tab_order(self):
        tab_order = self.load_and_get_tabs("test/tab_order/good_order.html")

        self.assertEqual(tab_order["/html/body/ul/li[1]"]["tab_place"], 0)
        self.assertEqual(tab_order["/html/body/ul/li[2]"]["tab_place"], 1)
        self.assertEqual(tab_order["/html/body/ul/li[3]"]["tab_place"], 2)
        self.assertEqual(tab_order["/html/body/ul/li[4]"]["tab_place"], 3)
        # Question: Are we okay with this being false? We could add a specific case for this?
        self.assertEqual(tab_order["/html/body"]["tab_place"], 4)

    def test_bad_tab_order(self):
        tab_order = self.load_and_get_tabs("test/tab_order/bad_order.html")

        self.assertEqual(tab_order["/html/body/ul/li[1]"]["tab_place"], 3)
        self.assertEqual(tab_order["/html/body/ul/li[2]"]["tab_place"], 0)
        self.assertEqual(tab_order["/html/body/ul/li[3]"]["tab_place"], 1)
        self.assertEqual(tab_order["/html/body/ul/li[4]"]["tab_place"], 2)
        self.assertEqual(tab_order["/html/body"]["tab_place"], 4)

    def test_good_outline(self):
        tab_order = self.load_and_get_tabs("test/tab_order/good_order.html")

        # The headful and headless browsers have different default focus outlines, so we just use the px  as truth
        self.assertTrue("1px" in tab_order["/html/body/ul/li[1]"]["focused_style_info"]["outline-style"])
        self.assertTrue("1px" in tab_order["/html/body/ul/li[2]"]["focused_style_info"]["outline-style"])
        self.assertTrue("1px" in tab_order["/html/body/ul/li[3]"]["focused_style_info"]["outline-style"])
        self.assertTrue("1px" in tab_order["/html/body/ul/li[4]"]["focused_style_info"]["outline-style"])

        self.assertTrue("0px" in tab_order["/html/body/ul/li[1]"]["focused_style_info"]["border-style"])
        self.assertTrue("0px" in tab_order["/html/body/ul/li[2]"]["focused_style_info"]["border-style"])
        self.assertTrue("0px" in tab_order["/html/body/ul/li[3]"]["focused_style_info"]["border-style"])
        self.assertTrue("0px" in tab_order["/html/body/ul/li[4]"]["focused_style_info"]["border-style"])

        # Check the unfocused styling information
        self.assertTrue("0px" in tab_order["/html/body/ul/li[1]"]["unfocused_style_info"]["outline-style"])
        self.assertTrue("0px" in tab_order["/html/body/ul/li[2]"]["unfocused_style_info"]["outline-style"])
        self.assertTrue("0px" in tab_order["/html/body/ul/li[3]"]["unfocused_style_info"]["outline-style"])
        self.assertTrue("0px" in tab_order["/html/body/ul/li[4]"]["unfocused_style_info"]["outline-style"])

        self.assertTrue("0px" in tab_order["/html/body/ul/li[1]"]["unfocused_style_info"]["border-style"])
        self.assertTrue("0px" in tab_order["/html/body/ul/li[2]"]["unfocused_style_info"]["border-style"])
        self.assertTrue("0px" in tab_order["/html/body/ul/li[3]"]["unfocused_style_info"]["border-style"])
        self.assertTrue("0px" in tab_order["/html/body/ul/li[4]"]["unfocused_style_info"]["border-style"])

    def test_no_outline(self):
        tab_order = self.load_and_get_tabs("test/tab_order/no_outline.html")

        self.assertEqual(tab_order["/html/body/ul/li[1]"]["focused_style_info"]["outline-style"], "rgb(0, 0, 0) none 0px")
        self.assertEqual(tab_order["/html/body/ul/li[2]"]["focused_style_info"]["outline-style"], "rgb(0, 0, 0) none 0px")
        self.assertEqual(tab_order["/html/body/ul/li[3]"]["focused_style_info"]["outline-style"], "rgb(0, 0, 0) none 0px")
        self.assertEqual(tab_order["/html/body/ul/li[4]"]["focused_style_info"]["outline-style"], "rgb(0, 0, 0) none 0px")

        self.assertEqual(tab_order["/html/body/ul/li[1]"]["focused_style_info"]["border-style"], "0px none rgb(0, 0, 0)")
        self.assertEqual(tab_order["/html/body/ul/li[2]"]["focused_style_info"]["border-style"], "0px none rgb(0, 0, 0)")
        self.assertEqual(tab_order["/html/body/ul/li[3]"]["focused_style_info"]["border-style"], "0px none rgb(0, 0, 0)")
        self.assertEqual(tab_order["/html/body/ul/li[4]"]["focused_style_info"]["border-style"], "0px none rgb(0, 0, 0)")

    def test_custom_outline(self):
        tab_order = self.load_and_get_tabs("test/tab_order/custom_border.html")

        self.assertEqual(tab_order["/html/body/ul/li[1]"]["focused_style_info"]["border-style"], "2px solid rgb(255, 0, 0)")
        self.assertEqual(tab_order["/html/body/ul/li[2]"]["focused_style_info"]["border-style"], "2px solid rgb(255, 0, 0)")
        self.assertEqual(tab_order["/html/body/ul/li[3]"]["focused_style_info"]["border-style"], "2px solid rgb(255, 0, 0)")
        self.assertEqual(tab_order["/html/body/ul/li[4]"]["focused_style_info"]["border-style"], "2px solid rgb(255, 0, 0)")

    def test_mass_links(self):
        # Lower max tab since it is slow
        self.controller.access._max_tabs = 30
        tab_order = self.load_and_get_tabs("test/tab_order/mass_links.html")

        # Test stop at some threshold
        self.assertEqual(30, len(tab_order))
        el = self.controller.access._driver.switch_to.active_element
        focus_xpath = self.controller.access._get_xpath_for_selenium_element(el)
        self.assertEqual(focus_xpath, "/html/body")

    def test_visible_on_focus(self):
        tab_order = self.load_and_get_tabs("test/tab_order/visible_on_focus.html")

        self.assertEqual(tab_order["/html/body/div[1]"]["position"]["x"], 8)
        self.assertEqual(tab_order["/html/body/div[1]"]["position"]["y"], 0)
        self.assertEqual(tab_order["/html/body/div[1]"]["tab_place"], 0)
        self.assertEqual(tab_order["/html/body/div[2]"]["tab_place"], 1)

    def test_visible_on_focus_delay(self):
        tab_order = self.load_and_get_tabs("test/tab_order/visible_on_focus_delay.html")

        self.assertEqual(tab_order["/html/body/div[1]"]["position"]["x"], 8)
        self.assertEqual(tab_order["/html/body/div[1]"]["position"]["y"], 0)
        self.assertEqual(tab_order["/html/body/div[1]"]["tab_place"], 0)
        self.assertEqual(tab_order["/html/body/div[2]"]["tab_place"], 1)

    # Possible Extra Tests:
    # 1. More difficult tab order test? What would this look like?
    # 2. Consider piecewise border? Example already built in piecewise_border.html

        
if __name__ == '__main__':
    unittest.main()
