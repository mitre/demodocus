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

from demodocusfw.web.dom_manipulations import (
    insert_after,
    insert_before,
    RE_BODY,
    RE_BODY_CLOSE,
    RE_HEAD,
    RE_HTML,
    RE_HTML_CLOSE
)


class TestDomManipulations(unittest.TestCase):
    """This tests helps make sure we inject our scripts in the right place."""

    node_to_insert = "<span id='test'/>"

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()

    def test_inject_script_after_html(self):
        html_code1 = f"""
        <html a1="" a2=""
        a3="" a4="">"""
        html_code2 = f"""<!--comment
        comment comment-->
            <head><!--comment--></head>
            <body><!--comment--></body>
        </html>"""
        html = html_code1 + html_code2
        result = insert_after(html, RE_HTML, self.node_to_insert)
        i = result.find(self.node_to_insert)
        self.assertEqual(i, len(html_code1))

    def test_inject_script_before_head(self):
        html_code1 = f"""
        <html a1="" a2=""
        a3="" a4="">
        <!--comment
        comment comment-->"""
        html_code2 = f"""<head><!--comment--></head>
            <body><!--comment--></body>
        </html>"""
        html = html_code1 + html_code2
        result = insert_before(html, RE_HEAD, self.node_to_insert)
        i = result.find(self.node_to_insert)
        self.assertEqual(i, len(html_code1))

    def test_inject_script_after_head(self):
        html_code1 = f"""
        <html a1="" a2=""
        a3="" a4="">
        <!--comment-->
            <head>"""
        html_code2 = f"""<!--comment
        comment comment--></head>
            <body><!--comment--></body>
        </html>"""
        html = html_code1 + html_code2
        result = insert_after(html, RE_HEAD, self.node_to_insert)
        i = result.find(self.node_to_insert)
        self.assertEqual(i, len(html_code1))

    def test_inject_script_after_body(self):
        html_code1 = f"""
        <html a1="" a2=""
        a3="" a4="">
        <!--comment-->
            <head><!--comment--></head>
            <body>"""
        html_code2 = f"""<!--comment
        comment comment --></body>
        </html>"""
        html = html_code1 + html_code2
        result = insert_after(html, RE_BODY, self.node_to_insert)
        i = result.find(self.node_to_insert)
        self.assertEqual(i, len(html_code1))

    def test_inject_script_before_body_close(self):
        html_code1 = f"""
        <html a1="" a2=""
        a3="" a4="">
        <!--comment-->
            <head><!--comment--></head>
            <body><!--comment
            comment comment -->"""
        html_code2 = f"""</body>
        </html>"""
        html = html_code1 + html_code2
        result = insert_before(html, RE_BODY_CLOSE, self.node_to_insert)
        i = result.find(self.node_to_insert)
        self.assertEqual(i, len(html_code1))

    def test_inject_script_before_html_close(self):
        html_code1 = f"""
        <html a1="" a2=""
        a3="" a4="">
        <!--comment-->
            <head><!--comment--></head>
            <body><!--comment--></body>
        """
        html_code2 = f"""</html>"""
        html = html_code1 + html_code2
        result = insert_before(html, RE_HTML_CLOSE, self.node_to_insert)
        i = result.find(self.node_to_insert)
        self.assertEqual(i, len(html_code1))


if __name__ == '__main__':
    unittest.main()
