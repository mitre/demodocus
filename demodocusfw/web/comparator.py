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

from io import StringIO
import logging

import jellyfish
from lxml import etree

from demodocusfw.comparator import BaseComparator
from .dom_manipulations import REACHABLE_ATT_NAME

logger = logging.getLogger('web.compare')


class XSLTComparator(BaseComparator):

    xslt_text = """
    <xsl:transform version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
        <xsl:strip-space elements="*"/>
        {}
    </xsl:transform>
    """

    def __init__(self, xslt_text=xslt_text):
        self.xslt_text = xslt_text
        self.tr = None

    # re_sub = re.compile(r'[;\s]+')

    def match(self, dom1, dom2):
        if self.tr is None:
            xslt = etree.XML(self.xslt_text)
            self.tr = etree.XSLT(xslt)

        dom1 = etree.parse(StringIO(dom1), parser=etree.HTMLParser())
        dom2 = etree.parse(StringIO(dom2), parser=etree.HTMLParser())
        # dom1 = etree.XML(dom1)
        # dom2 = etree.XML(dom2)
        strdom1 = str(self.tr(dom1))
        strdom2 = str(self.tr(dom2))

        match_result = strdom1 == strdom2

        logger.debug("Running a {} with:\ndom1 = [\n\t{}\n\t   ]\ndom2 = [\n\t{}\n\t   ]\nreturned = {}\n".format(\
            self.__class__.__name__, strdom1, strdom2, match_result))

        return match_result
        # return self.re_sub.sub('', str(self.tr(dom1))) == self.re_sub.sub('', str(self.tr(dom2)))


class DOMStructureComparator(XSLTComparator):
    # This comparator compares all reachable nodes in the two documents.
    # It does not consider their attributes.
    # https://stackoverflow.com/questions/13093091/lxml-or-lxml-html-print-tree-structure/13134559#13134559
    # https://developer.mozilla.org/en-US/docs/Web/XSLT/Element/copy
    # Explanation:
    #   Copy makes a copy of the nodes without attributes.
    #   Apply-templates recurses on children.
    #   The second template catches all cases we DON'T want to copy.
    def __init__(self):
        super(DOMStructureComparator, self).__init__(XSLTComparator.xslt_text.format(
            f"""
            <xsl:template match="*">
                <xsl:copy>
                    <xsl:apply-templates select="*"/>
                </xsl:copy>
            </xsl:template>
            <xsl:template match="*[self::head or self::style or self::script or @{REACHABLE_ATT_NAME}='false']"/>
            """))
        self.tr = None


# TODO: Capitalization? Spacing? Punctuation?
class TextComparator(XSLTComparator):

    # This comparator compares all text nodes in the document, even hidden ones.
    def __init__(self):
        super(TextComparator, self).__init__(XSLTComparator.xslt_text.format(
            f"""
            <xsl:template match="//text()">
                <xsl:copy>
                </xsl:copy>
            </xsl:template>
            <xsl:template match="*[self::head or self::style or self::script or @{REACHABLE_ATT_NAME}='false']/text()"/>
            """))
        self.tr = None


class FlexibleTextComparator(XSLTComparator):

    # static functions so the user doesnt need to import jellyfish
    levenshtein_distance = jellyfish.levenshtein_distance
    damerau_levenshtein_distance = jellyfish.damerau_levenshtein_distance
    hamming_distance = jellyfish.hamming_distance
    jaro_distance = jellyfish.jaro_distance
    jaro_winkler = jellyfish.jaro_winkler
    dist_funcs = [levenshtein_distance,
                  damerau_levenshtein_distance,
                  hamming_distance,
                  jaro_distance,
                  jaro_winkler]

    # This comparator compares all text nodes in the document, even hidden ones.
    def __init__(self, dist_func=levenshtein_distance, max_operations=10, min_threshold=0.9):
        super(FlexibleTextComparator, self).__init__(XSLTComparator.xslt_text.format(
            f"""
            <xsl:template match="//text()">
                <xsl:copy>
                </xsl:copy>
            </xsl:template>
            <xsl:template match="*[self::head or self::style or self::script or @{REACHABLE_ATT_NAME}='false']/text()"/>
            """))

        self.dist_func = dist_func
        self.max_operations = max_operations
        self.min_threshold = min_threshold
        self.tr = None

    @property
    def dist_func(self):
        return self._dist_func


    @dist_func.setter
    def dist_func(self, dist_func):
        assert dist_func in self.dist_funcs, f'dist_func ' + \
            f'({str(dist_func)}) needs to be in the set of acceptable distance ' + \
            f'functions:\n  ' + '\n  '.join(['FlexibleTextComparator.' + i.__name__ for i in self.dist_funcs])
        self._dist_func = dist_func

    @property
    def max_operations(self):
        return self._max_operations

    @max_operations.setter
    def max_operations(self, max_operations):
        assert max_operations >= 0, 'max_operations must be >= 0'
        self._max_operations = max_operations

    @property
    def min_threshold(self):
        return self._min_threshold

    @min_threshold.setter
    def min_threshold(self, min_threshold):
        assert 0 <= min_threshold <= 1, 'min_threshold must be >= 0 and <= 1'
        self._min_threshold = min_threshold

    def match(self, dom1, dom2):

        if self.tr is None:
            xslt = etree.XML(self.xslt_text)
            self.tr = etree.XSLT(xslt)

        dom1 = etree.parse(StringIO(dom1), parser=etree.HTMLParser())
        dom2 = etree.parse(StringIO(dom2), parser=etree.HTMLParser())
        # dom1 = etree.XML(dom1)
        # dom2 = etree.XML(dom2)
        #strdom1 = str(self.tr(dom1))
        #strdom2 = str(self.tr(dom2))

        strdom1 = ''.join(str(self.tr(dom1)).split())
        strdom2 = ''.join(str(self.tr(dom2)).split())

        if strdom1[0:20] == '<?xmlversion="1.0"?>':
            strdom1 = strdom1[20:]

        if strdom2[0:20] == '<?xmlversion="1.0"?>':
            strdom2 = strdom2[20:]

        dist = self.dist_func(strdom1, strdom2)

        # distance functions that output number of differencs/operations
        if self.dist_func in self.dist_funcs[0:3]:
            dist_ratio = 1 - (dist / max(len(strdom1), len(strdom2)))
            result_match = dist <= self.max_operations and \
                dist_ratio >= self.min_threshold
        # distance functions that output a similarity score
        else:
            result_match = dist >= self.min_threshold

        logger.debug("Running a {} with:\n".format(self.__class__.__name__) + \
                    "dom1 = [\n\t{}\n\t   ]\n".format(strdom1) + \
                    "dom2 = [\n\t{}\n\t   ]\n".format(strdom2) + \
                    "function = {}\n".format(self.dist_func.__name__) + \
                    "max_operations = {}\n".format(self.max_operations) + \
                    "min_threshold = {}\n".format(self.min_threshold) + \
                    "dist = {}\n".format(str(dist)) + \
                    "returned = {}\n".format(str(result_match))
                    )

        return result_match
