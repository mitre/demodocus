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

from demodocusfw.web.template import HtmlTemplate


class TestTemplate(unittest.TestCase):

    _attributes_to_match_backup = None

    @classmethod
    def setUpClass(cls):
        # For these tests we don't want to ignore any attributes when matching.
        cls._attributes_to_match_backup = HtmlTemplate.ATTRIBUTES_TO_MATCH
        HtmlTemplate.ATTRIBUTES_TO_MATCH = None

    @classmethod
    def tearDownClass(cls):
        # Put back the old attributes to match.
        HtmlTemplate.ATTRIBUTES_TO_MATCH = cls._attributes_to_match_backup

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()

    @staticmethod
    def _createHtml(html):
        return """<html><body>{}</body></html>""".format(html)

    def test_stable(self):
        # Add two of the same thing and make sure the template is the same.
        s = self._createHtml("""<span id="span1">text1</span>""")
        html1 = s
        html2 = s
        template = HtmlTemplate(html1, html2)
        self.assertTrue(template.is_stable())
        self.assertEqual(str(template), s)

    def test_unstable_text(self):
        # The text from both versions are combined.
        html1 = self._createHtml("""<span id="span1">text1</span>""")
        html2 = self._createHtml("""<span id="span1">text2</span>""")
        template = HtmlTemplate(html1, html2)
        self.assertFalse(template.is_stable())
        self.assertEqual(str(template), self._createHtml("""<span id="span1" unstable_text="true">text1||text2</span>"""))
        self.assertTrue("/html/body/span" in template.get_unstable_xpaths())
        self.assertTrue(template.matches_html(html1))
        self.assertTrue(template.matches_html(html2))
        # This template should now match any text in the span.
        html3 = self._createHtml("""<span id="span1">text3</span>""")
        self.assertTrue(template.matches_html(html3))

    def test_unstable_attribute(self):
        # The attributes from both versions are combined.
        html1 = self._createHtml("""<span id="span1">text1</span>""")
        html2 = self._createHtml("""<span id="span2" att1="a">text1</span>""")
        template = HtmlTemplate(html1, html2)
        self.assertFalse(template.is_stable())
        # Check to make sure the span has all the attributes.
        span = template.xpath("//span")[0]
        self.assertTrue("id" in span.attrib and span.attrib["id"] == "span1||span2")
        self.assertTrue("att1" in span.attrib and span.attrib["att1"] == "a")
        self.assertTrue("unstable_attributes" in span.attrib and span.attrib["unstable_attributes"] == "att1 id")
        self.assertTrue(template.matches_html(html1))
        self.assertTrue(template.matches_html(html2))
        # This template should now match any value for id.
        # This template should match with or without att1, and any value for att1.
        self.assertTrue(template.matches_html(self._createHtml("""<span id="span3">text1</span>""")))
        self.assertTrue(template.matches_html(self._createHtml("""<span id="span4" att1="bc">text1</span>""")))
        # This template should not match other attributes.
        self.assertFalse(template.matches_html(self._createHtml("""<span id="span3" att2="a">text3</span>""")))

    def test_unstable_text_and_attribute(self):
        # The text and attributes from both versions are combined.
        html1 = self._createHtml("""<span id="span1">text1</span>""")
        html2 = self._createHtml("""<span id="span2">text2</span>""")
        template = HtmlTemplate(html1, html2)
        self.assertFalse(template.is_stable())
        self.assertEqual(
            str(template),
            self._createHtml("""<span id="span1||span2" unstable_attributes="id" unstable_text="true">text1||text2</span>""")
        )
        self.assertTrue(template.matches_html(html1))
        self.assertTrue(template.matches_html(html2))
        # This template should now match any value for id.
        # This template should now match any text.
        self.assertTrue(template.matches_html(self._createHtml("""<span id="span3">text3</span>""")))
        # This template should not match other attributes.
        self.assertFalse(template.matches_html(self._createHtml("""<span id="span3" att1="a">text3</span>""")))

    def test_inserted_child(self):
        # The added element is marked unstable.
        html1 = self._createHtml("""<span id="span1">text1</span>""")
        html2 = self._createHtml("""<div></div><span id="span1">text1</span>""")
        template = HtmlTemplate(html1, html2)
        self.assertFalse(template.is_stable())
        self.assertEqual(
            str(template),
            self._createHtml("""<div unstable_element="true"/><span id="span1">text1</span>""")
        )
        self.assertTrue(template.matches_html(html1))
        self.assertTrue(template.matches_html(html2))
        # This template should now allow a match with or without that element.
        # This template can also detect if that elements changes places (within one place).
        self.assertTrue(template.matches_html(self._createHtml("""<span id="span1">text1</span><div/>""")))
        # This template should not match a different element, or other additional elements.
        self.assertFalse(template.matches_html(self._createHtml("""<span/><span id="span1">text1</span>""")))
        self.assertFalse(template.matches_html(self._createHtml("""<div/><span id="span1">text1</span><div/>""")))

    def test_deleted_child(self):
        # The removed element is marked unstable.
        html1 = self._createHtml("""<div></div><span id="span1">text1</span>""")
        html2 = self._createHtml("""<span id="span1">text1</span>""")
        template = HtmlTemplate(html1, html2)
        self.assertFalse(template.is_stable())
        self.assertEqual(
            str(template),
            self._createHtml("""<div unstable_element="true"/><span id="span1">text1</span>""")
        )
        self.assertTrue(template.matches_html(html1))
        self.assertTrue(template.matches_html(html2))
        # Since the template is the same as the inserted child, no reason to do additional tests here.

    def test_moved_child_1(self):
        # The first moving element is marked unstable.
        html1 = self._createHtml("""<div></div><span id="span1">text1</span>""")
        html2 = self._createHtml("""<span id="span1">text1</span><div></div>""")
        template = HtmlTemplate(html1, html2)
        self.assertFalse(template.is_stable())
        self.assertEqual(
            str(template),
            self._createHtml("""<div unstable_element="true"/><span id="span1">text1</span>""")
        )
        self.assertTrue(template.matches_html(html1))
        self.assertTrue(template.matches_html(html2))
        # Since the template is the same as the inserted child, no reason to do additional tests here.

    def test_moved_child_2(self):
        # The first moving element is marked unstable.
        html1 = self._createHtml("""<span id="span1">text1</span><div></div>""")
        html2 = self._createHtml("""<div></div><span id="span1">text1</span>""")
        template = HtmlTemplate(html1, html2)
        self.assertFalse(template.is_stable())
        self.assertEqual(
            str(template),
            self._createHtml("""<span id="span1" unstable_element="true">text1</span><div/>""")
        )
        self.assertTrue(template.matches_html(html1))
        self.assertTrue(template.matches_html(html2))
        # Since the template is the basically same as the inserted child, no reason to do additional tests here.

    def test_replaced_child(self):
        # The different elements in both versions appear and are marked unstable.
        html1 = self._createHtml("""<span></span><span id="span1">text1</span>""")
        html2 = self._createHtml("""<div></div><span id="span1">text1</span>""")
        template = HtmlTemplate(html1, html2)
        self.assertFalse(template.is_stable())
        self.assertEqual(
            str(template),
            self._createHtml("""<span unstable_element="true"/><div unstable_element="true"/><span id="span1">text1</span>""")
        )
        self.assertTrue(template.matches_html(html1))
        self.assertTrue(template.matches_html(html2))
        # This template would match either element, or both elements, or neither.
        self.assertTrue(template.matches_html("""<span/><div/><span id="span1">text1</span>"""))
        self.assertTrue(template.matches_html("""<div/><span/><span id="span1">text1</span>"""))
        self.assertTrue(template.matches_html("""<span id="span1">text1</span>"""))
        self.assertTrue(template.matches_html("""<span id="span1">text1</span><div/><span/>"""))

    def test_update_1(self):
        # If there are no unstable items in the tree, it should just get overwritten with html2.
        html1 = self._createHtml("""<span id="span1">text1</span>""")
        html2 = self._createHtml("""<span id="span1">text2</span>""")
        template = HtmlTemplate(html1)
        template = template.get_updated_template(html2)
        self.assertEqual(str(template), html2)

    def test_update_2(self):
        # Any unstable items in the tree should remain unstable.
        # In this case the text should remain unstable.
        html1 = self._createHtml("""<span id="span1" unstable_text="true">text1</span>""")
        html2 = self._createHtml("""<span id="span1">text2</span>""")
        template = HtmlTemplate(html1)
        template = template.get_updated_template(html2)
        self.assertEqual(str(template),
                         self._createHtml("""<span id="span1" unstable_text="true">text1||text2</span>"""))

    def test_update_3(self):
        # Stable items should be overwritten, while unstable items should remain unstable.
        # In this case, the text should remain unstable, but the id should be overwritten.
        html1 = self._createHtml("""<span id="span1" unstable_text="true">text1</span>""")
        html2 = self._createHtml("""<span id="span2">text2</span>""")
        template = HtmlTemplate(html1)
        template = template.get_updated_template(html2)
        self.assertEqual(str(template),
                         self._createHtml("""<span id="span2" unstable_text="true">text1||text2</span>"""))

    def test_update_4(self):
        # Elements not present in tree2 should be deleted, while elements not present in tree1 should be added.
        # Elements marked unstable should be merged.
        # In this case,
        #   the first span from html1 should be removed
        #   one of the divs in html2 should match the unstable div in html1
        #   the other div should be added
        #   the span text should be merged
        html1 = self._createHtml("""<span></span><span id="span1" unstable_text="true">text1</span><div unstable_element="true"></div>""")
        html2 = self._createHtml("""<div></div><div></div><span id="span1">text2</span>""")
        template = HtmlTemplate(html1)
        template = template.get_updated_template(html2)
        # The output should be something like:
        # <div/><span id="span1" unstable_text="true">text1||text2</span><div unstable_element="true"/>
        # Check that there are two divs.
        self.assertEqual(len(template.xpath("//div")), 2)
        # One of the divs should be marked unstable.
        self.assertEqual(len(template.xpath("//div[@unstable_element]")), 1)
        spans = template.xpath("//span")
        # Check that there's one span
        self.assertEqual(len(spans), 1)
        # That span should have unstable text.
        self.assertTrue("unstable_text" in spans[0].attrib)
        # The text should be text1||text2.
        self.assertEqual(spans[0].text, "text1||text2")


if __name__ == '__main__':
    unittest.main()
