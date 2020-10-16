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
from demodocusfw.web.dom_manipulations import (
    js_calculate_reachable,
    REACHABLE_ATT_NAME
)
from demodocusfw.web.utils import serve_output_folder
from demodocusfw.web.web_access import ChromeWebAccess


class TestReachable(unittest.TestCase):
    """This tests helps make sure we are correctly setting the _reachable flag on elements."""

    node_to_insert = "<span id='test'/>"

    @classmethod
    def setUpClass(cls):
        # Set up a server to serve up output data.
        cls.output_server = serve_output_folder(config)
        cls.web_access = ChromeWebAccess(config)
        cls.web_access._create_driver(config)

    @classmethod
    def tearDownClass(cls):
        cls.web_access.shutdown()
        cls.output_server.stop()
        config.OUTPUT_DIR.cleanup()

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()
        # Clear the page.
        self.web_access._driver.get("about:blank")

    def tearDown(self):
        pass

    def _inject_and_test(self, html_code):
        # There should be a button at document/body/button[0] that is not reachable.
        self.assertTrue(self.web_access.set_page_source(html_code))
        self.web_access.run_js(js_calculate_reachable)
        button = self.web_access.run_js("return document.getElementById('button');")
        self.assertEqual(button.get_attribute(REACHABLE_ATT_NAME), "false")

    def test_reachable_display_none(self):
        html_code = """<html><head></head><body><button id="button" style="display:none"/></body></html>"""
        self._inject_and_test(html_code)

    def test_reachable_visibility_hidden(self):
        html_code = """<html><head></head><body><button id="button" style="visibility:hidden"/></body></html>"""
        self._inject_and_test(html_code)

    def test_reachable_visibility_collapsed(self):
        html_code = """<html><head></head><body><button id="button" style="visibility:collapse"/></body></html>"""
        self._inject_and_test(html_code)

    def test_reachable_script_display_none(self):
        html_code = """<html><head></head><body><button id="button"/>
        <script>document.getElementById("button").style.display="none";</script></body></html>"""
        self._inject_and_test(html_code)

    def test_reachable_parent_display_none(self):
        html_code = """<html><head></head><body><div style="display:none"><button id="button"/></div></body></html>"""
        self._inject_and_test(html_code)

    def test_reachable_blocked(self):
        html_code = """<html><head></head><body>
        <button id="button"/>
        <button id="overlay" style="position:absolute;z-index:1000;top:0px;left:0px;width:100%;height:100%;background-color:blue;opacity:0.8;"/>
        </body></html>"""
        self._inject_and_test(html_code)


if __name__ == '__main__':
    unittest.main()
