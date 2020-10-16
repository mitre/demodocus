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

from .config import mode_crawler_single as config
from demodocusfw.web.server import ThreadedHTTPServer
from demodocusfw.crawler import Crawler
from demodocusfw.web import dom_manipulations
from demodocusfw.web.dom_manipulations import REACHABLE_ATT_NAME
from demodocusfw.web.utils import serve_output_folder
from demodocusfw.web.web_access import ChromeWebAccess


class TestEventTracking(unittest.TestCase):
    event_code = "console.log('Test');"

    ep_template = 'http://{}:{}/demodocusfw/tests/sandbox/test/css_pseudo_classes/{}/example.html'

    @classmethod
    def setUpClass(cls):
        # Set up a server to serve up the examples.
        cls.examples_server = ThreadedHTTPServer('localhost', 0)
        cls.server_ip, cls.server_port = cls.examples_server.server.server_address
        print('server_ip: {}'.format(cls.server_ip))
        print('server_port: {}'.format(cls.server_port))
        cls.examples_server.start()

    @classmethod
    def tearDownClass(cls):
        cls.examples_server.stop()

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()
        # Set up a server to serve up output data.
        self.output_server = serve_output_folder(config)
        # Now create the web access.
        self.web_access = ChromeWebAccess(config)
        self.web_access._create_driver(config)

    def tearDown(self):
        self.web_access.shutdown()
        self.output_server.stop()
        config.OUTPUT_DIR.cleanup()

    def format_ep(self, path):
        return self.ep_template.format(self.server_ip, self.server_port, path)

    def _inject_code(self, html_code):
        html_code = dom_manipulations.manage_event_listeners(html_code)
        self.assertTrue(self.web_access.set_page_source(html_code))

    def test_event_as_jQuery(self):
        """Tests whether we capture the click event when added with jquery."""
        js = "$('#button').click(function() { " + self.event_code + " });"
        html_code = f"""<html><head><script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script></head><body><button id="button" {REACHABLE_ATT_NAME}="true"></button><script>{js}</script></body></html>"""
        self._inject_code(html_code)
        self.assertTrue(list(self.web_access.get_elements_supporting_js_event('click'))[0].xpath == "/html/body/button")

    def test_event_hover_jquery(self):
        """Tests whether we capture the hover event when added with jquery"""
        js = """$('#button').hover(
            function() {
                console.log('Test: hover in');
            },
            function() {
                console.log('Test: hover out');
            });"""
        html_code = f"""<html><head><script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script></head><body><button id="button" {REACHABLE_ATT_NAME}="true"></button><script>{js}</script></body></html>"""
        self._inject_code(html_code)
        self.assertTrue(list(self.web_access.get_elements_supporting_js_event('mouseover'))[0].xpath == "/html/body/button")
        self.assertTrue(list(self.web_access.get_elements_supporting_js_event('mouseout'))[0].xpath == "/html/body/button")

    def test_event_as_js_onclick(self):
        """Tests whether we capture the click event when added with javascript property."""
        js = "document.getElementById('button').onclick = function() { " + self.event_code + " };"
        html_code = f"""<html><head></head><body><button id="button" {REACHABLE_ATT_NAME}="true"></button><script>{js}</script></body></html>"""
        self._inject_code(html_code)
        self.assertTrue(list(self.web_access.get_elements_supporting_js_event('click'))[0].xpath == "/html/body/button")

    def test_event_as_addEventListener(self):
        """Tests whether we capture the click event when added with the addEventListener function."""
        js = "document.getElementById('button').addEventListener('click', function() { " + self.event_code + " });"
        html_code = f"""<html><head></head><body><button id="button" {REACHABLE_ATT_NAME}="true"></button><script>{js}</script></body></html>"""
        self._inject_code(html_code)
        self.assertTrue(list(self.web_access.get_elements_supporting_js_event('click'))[0].xpath == "/html/body/button")

    def test_event_as_attribute(self):
        """Tests whether we capture the click event when added as an attribute."""
        html_code = f"""<html><head></head><body><button id="button" {REACHABLE_ATT_NAME}="true" onclick="{self.event_code}"></button></body></html>"""
        self._inject_code(html_code)
        self.assertTrue(list(self.web_access.get_elements_supporting_js_event('click'))[0].xpath == "/html/body/button")

    def test_event_before_append(self):
        """Tests whether we capture the click event if it is set before the element is added to the page."""
        html_code = f"""
        <html>
        <head></head>
        <body>
        <script>
        var btn = document.createElement("button");
        btn.onclick = "{self.event_code}";
        btn.setAttribute("{REACHABLE_ATT_NAME}", true);
        document.body.appendChild(btn);
        </script>
        </body></html>"""
        self._inject_code(html_code)
        self.assertTrue(list(self.web_access.get_elements_supporting_js_event('click'))[0].xpath == "/html/body/button")

    def test_css_pseudo_hover_list(self):
        # Test base case of a list being expanded, this is the simplest pseudo class case
        # Form: Selector:hover Applied
        url = "hover_list"
        entry_point = self.format_ep(url)
        crawler = Crawler(config)
        crawler.crawl_all([entry_point])

        self.assertEqual(2, len(crawler.controller.graph.get_states()))

    def test_css_pseudo_hover_list_combo_child(self):
        # Tests for having combos of
        # Example Form: .dropdown:hover ul, .dropdown2:hover > ul {style}

        url = "hover_list_combo_child"
        entry_point = self.format_ep(url)
        crawler = Crawler(config)
        crawler.crawl_all([entry_point])

        # There are three states: 0, first list expanded, second list expanded.
        self.assertEqual(3, len(crawler.controller.graph.get_states()))

    def test_css_pseudo_hover_list_not(self):
        # Tests for pairing additional pseudo classes
        # Example form: .dropdown:hover:not(#nodrop):not(.nodrop) .dropdown-content

        url = "hover_list_not"
        entry_point = self.format_ep(url)
        crawler = Crawler(config)
        crawler.crawl_all([entry_point])

        # There are three states: 0, first list expanded, second list expanded.
        self.assertEqual(3, len(crawler.controller.graph.get_states()))

    def test_css_pseudo_hover_list_media(self):
        # Tests for css rules that may use media rules
        # Example form: @media screen and (min-width: 200px) {selector:hover {styling}}

        url = "hover_list_media"
        entry_point = self.format_ep(url)
        crawler = Crawler(config)
        crawler.crawl_all([entry_point])

        # There are three states: 0, first list expanded, second list expanded.
        self.assertEqual(3, len(crawler.controller.graph.get_states()))

    def test_css_pseudo_hover_list_sibling(self):
        # Tests for css that use sibling selector (+)
        # Example form: div + ul {style}

        url = "hover_list_sibling"
        entry_point = self.format_ep(url)
        crawler = Crawler(config)
        crawler.crawl_all([entry_point])

        self.assertEqual(2, len(crawler.controller.graph.get_states()))

    def test_css_pseudo_hover_list_preceded(self):
        # Tests for css that use precedence selector (~)
        # Example form: div ~ ul {style}

        url = "hover_list_preceded"
        entry_point = self.format_ep(url)
        crawler = Crawler(config)
        crawler.crawl_all([entry_point])

        self.assertEqual(2, len(crawler.controller.graph.get_states()))


if __name__ == '__main__':
    unittest.main()
