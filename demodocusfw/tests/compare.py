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

import json
from sys import stdout
import unittest

from demodocusfw.comparator import CompareFlag, Comparer, StrictComparator
from demodocusfw.web.comparator import (
    DOMStructureComparator,
    FlexibleTextComparator,
    TextComparator
)
from demodocusfw.web.dom_manipulations import REACHABLE_ATT_NAME


class TestCompare(unittest.TestCase):

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()

    def _createHtml(self, html):
        return """
        <html>
            <head>
            </head>
            <body>
                {}
            </body>
        </html>
        """.format(html)

    def _compareStates(self, file_path):

        with open(file_path, 'r') as f:
            file_content = json.load(f)

        test_pipeline = [
            (StrictComparator(), CompareFlag.STOP_IF_TRUE),
            (DOMStructureComparator(), CompareFlag.STOP_IF_FALSE),
            (TextComparator(), CompareFlag.STOP_IF_FALSE),
            (FlexibleTextComparator(), CompareFlag.STOP_IF_FALSE)
        ]

        comparer = Comparer()
        errorList = []

        for i in range(0, len(file_content['recordings'])):
            html1 = file_content['recordings'][i]

            equivalent_array = []
            for array in file_content['equivalent']:
                if(i in array):
                    equivalent_array = array
                    break

            for x in range(0, len(file_content['recordings'])):
                html2 = file_content['recordings'][x]

                try:
                    if i == x or x in equivalent_array:
                        self.assertTrue(comparer.compare(html1, html2, test_pipeline))
                    else:
                        self.assertFalse(comparer.compare(html1, html2, test_pipeline))
                except AssertionError:
                    errorList.append(f'Error comparing state {i} and state {x}')

        if len(errorList) > 0:
            print(errorList)
            raise AssertionError

    """ StrictComparator """

    def test_StrictComparator_semicolon(self):
        """ Semicolons should not make a difference. """
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;"/>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none"/>""")
        self.assertTrue(StrictComparator().match(html1, html2))

    def test_StrictComparator_space(self):
        """ Whitespace characters should not make a difference. """
        html1 = self._createHtml("""<div id="test" class="test" style="display:none">Hello World!</div>""")
        html2 = self._createHtml("""<div id="test"  class="test"  style="display: none">\n\tHello  World!\n\t</div>""")
        self.assertTrue(StrictComparator().match(html1, html2))

    def test_StrictComparator_display_changed(self):
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;"/>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:block;"/>""")
        self.assertFalse(StrictComparator().match(html1, html2))

    def test_StrictComparator_content_changed(self):
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world</div>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        self.assertFalse(StrictComparator().match(html1, html2))

    """ DOMStructureComparator """

    def test_DOMStructureComparator_content(self):
        """ Should ignore content. """
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;"/>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        self.assertTrue(DOMStructureComparator().match(html1, html2))

    def test_DOMStructureComparator_attributes(self):
        """ Should ignore attributes. """
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;"/>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:block;"/>""")
        self.assertTrue(DOMStructureComparator().match(html1, html2))

    def test_DOMStructureComparator_reachable(self):
        """ Should ignore elements marked not reachable. """
        html1 = self._createHtml(f"""<div id="test" class="test" style="display:none;" {REACHABLE_ATT_NAME}="false"/>""")
        html2 = self._createHtml("""""")
        self.assertTrue(DOMStructureComparator().match(html1, html2))

    def test_DOMStructureComparator_structure_changed(self):
        html1 = self._createHtml("""<div id="test" class="test"><div id="innerDiv"/></div>""")
        html2 = self._createHtml("""<div id="test" class="test"/>""")
        self.assertFalse(DOMStructureComparator().match(html1, html2))

    def test_DOMStructureComparator_reachable_changed(self):
        html1 = self._createHtml(f"""<div id="test" class="test" style="display:none;" {REACHABLE_ATT_NAME}="false"/>""")
        html2 = self._createHtml(f"""<div id="test" class="test" style="display:none;" {REACHABLE_ATT_NAME}="true"/>""")
        self.assertFalse(DOMStructureComparator().match(html1, html2))

    """ TextComparator """

    def test_TextComparator(self):
        """ Should ignore everything besides text content. """
        html1 = self._createHtml("""<div>Hello </div><div>World</div>""")
        html2 = self._createHtml("""<div id="test" class="test2" style="display:block;">Hello World</div>""")
        self.assertTrue(TextComparator().match(html1, html2))

    def test_TextComparator_changed(self):
        """ Any change in text should be detected. """
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world</div>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        self.assertFalse(TextComparator().match(html1, html2))

    """ FlexibleTextComparator """

    def test_FlexibleTextComparator_jaro(self):
        """ Should ignore everything besides text content. """
        html1 = self._createHtml("""<div>Hello </div><div>World</div>""")
        html2 = self._createHtml("""<div id="test" class="test2" style="display:block;">Hello World</div>""")
        dist_func = FlexibleTextComparator.jaro_distance
        self.assertTrue(FlexibleTextComparator(dist_func, min_threshold = 0.999).match(html1, html2))

    def test_FlexibleTextComparator_jaro_changed(self):
        """ Any change in text should be detected. """
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world</div>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        dist_func = FlexibleTextComparator.jaro_distance
        self.assertFalse(FlexibleTextComparator(dist_func, min_threshold = 0.999).match(html1, html2))

    def test_FlexibleTextComparator_jaro_changed_low_threshold(self):
        """ Any change in text should be detected. """
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world</div>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        dist_func = FlexibleTextComparator.jaro_distance
        self.assertTrue(FlexibleTextComparator(dist_func, min_threshold = 0.6).match(html1, html2))

    def test_FlexibleTextComparator_levenshtein(self):
        """ Should ignore everything besides text content. """
        html1 = self._createHtml("""<div>Hello </div><div>World</div>""")
        html2 = self._createHtml("""<div id="test" class="test2" style="display:block;">Hello World</div>""")
        dist_func = FlexibleTextComparator.levenshtein_distance
        self.assertTrue(FlexibleTextComparator(dist_func, max_operations = 0).match(html1, html2))

    def test_FlexibleTextComparator_levenshtein_changed(self):
        """ Any change in text should be detected. """
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world</div>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        dist_func = FlexibleTextComparator.levenshtein_distance
        self.assertFalse(FlexibleTextComparator(dist_func, max_operations = 0).match(html1, html2))

    def test_FlexibleTextComparator_levenshtein_changed_low_operations(self):
        """ Any change in text should be detected. """
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world</div>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        dist_func = FlexibleTextComparator.levenshtein_distance
        self.assertTrue(FlexibleTextComparator(dist_func, max_operations = 1).match(html1, html2))


    """ Pipelines """

    def test_pipeline1(self):
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world</div>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        test_pipeline = [
            (StrictComparator(), CompareFlag.STOP_IF_TRUE)
        ]
        self.assertFalse(Comparer.compare(html1, html2, test_pipeline))

    def test_pipeline2(self):
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world</div>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        test_pipeline = [
            (StrictComparator(),          CompareFlag.STOP_IF_TRUE),
            (DOMStructureComparator(),    CompareFlag.STOP_IF_FALSE)
        ]
        self.assertTrue(Comparer().compare(html1, html2, test_pipeline))

    def test_pipeline3(self):
        html1 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world</div>""")
        html2 = self._createHtml("""<div id="test" class="test" style="display:none;">Hello world!</div>""")
        test_pipeline = [
            (StrictComparator(),          CompareFlag.STOP_IF_TRUE),
            (DOMStructureComparator(),    CompareFlag.STOP_IF_FALSE),
            (TextComparator(),            CompareFlag.STOP_IF_FALSE)
        ]
        self.assertFalse(Comparer().compare(html1, html2, test_pipeline))


if __name__ == '__main__':
    unittest.main()
