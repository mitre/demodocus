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
import time
import unittest

from .config import mode_crawler_single as config
from demodocusfw.web.utils import serve_output_folder
from demodocusfw.web.web_access import ChromeWebAccess


class TestAnimation(unittest.TestCase):
    """
    This unit test tests several different kinds and speeds of animations to make sure
    that the crawler always waits for the animation to complete.
    """

    @classmethod
    def setUpClass(cls):
        # Set up a server to serve up output data.
        cls.output_server = serve_output_folder(config)
        # Now create the web access.
        cls.web_access = ChromeWebAccess(config)
        cls.web_access._create_driver(config)

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()

    @classmethod
    def tearDownClass(cls):
        cls.web_access.shutdown()
        cls.output_server.stop()
        config.OUTPUT_DIR.cleanup()

    def test_crawl_css_transition(self):
        # A div that grows from a start width to an end width when the page loads, using css transitions.
        start_width_px = 1
        end_width_px = 570
        css_transition_page_source = """
        <html>
            <head>
                <!-- taken from https://www.w3schools.com/jsref/tryit.asp?filename=tryjsref_style_transitionduration -->
                <style>
                .myDIV-start {
                  border: 1px solid black;
                  background-color: lightblue;
                  width: {START_WIDTH_PX}px;
                  height: 200px;
                  overflow: auto;
                }

                .myDIV-animate {
                  border: 1px solid black;
                  background-color: coral;
                  height: 200px;
                  width: {END_WIDTH_PX}px;
                  overflow: auto;
                  transition-timing-function: cubic-bezier(0.39, 0.575, 0.565, 1);
                  transition-duration: {TIME_MS}ms;
                }
                </style>
            </head>
            <body onload="document.getElementById('myDIV').className='myDiv-animate'">
                <div id="myDIV" class="myDIV-start">
                </div>
            </body>
        </html>
            """.replace("{START_WIDTH_PX}", str(start_width_px)).replace("{END_WIDTH_PX}", str(end_width_px))

        """ Try to crawl a css transition. """
        # Clear the page. Otherwise the transition timing will be off.
        self.web_access._driver.get("about:blank")
        # Inject the dom.
        html_code = css_transition_page_source.replace("{TIME_MS}", "400")
        t0 = time.time()
        self.assertTrue(self.web_access.set_page_source(html_code))
        t1 = time.time()
        self.assertGreaterEqual((t1-t0)*1000, 400)
        # Check the page to make sure the transition has completed.
        width = self.web_access.run_js("return window.getComputedStyle(document.getElementById('myDIV'))['width']")
        self.assertEqual(width, str(end_width_px) + "px")

        # Try again with a a slower time.
        self.web_access._driver.get("about:blank")
        html_code = css_transition_page_source.replace("{TIME_MS}", "4000")
        t0 = time.time()
        self.assertTrue(self.web_access.set_page_source(html_code))
        t1 = time.time()
        self.assertGreaterEqual((t1-t0)*1000, 4000)
        # Check the page to make sure the transition has completed.
        width = self.web_access.run_js("return window.getComputedStyle(document.getElementById('myDIV'))['width']")
        self.assertEqual(width, str(end_width_px) + "px")


if __name__ == '__main__':
    unittest.main()
