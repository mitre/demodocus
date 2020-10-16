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

from copy import deepcopy
import re

from lxml import etree
import lxml.html

from demodocusfw.web.utils import clean_html


class HtmlTemplate:
    """
    Class HtmlTemplate

    HtmlTemplate is a class for intelligently handling html documents. It allows for content that changes on
    a page over time or across page loads. We call this *unstable* content. Unstable content gets marked up
    in the HtmlTemplate's _full_tree so we can keep track of it.

    HtmlTemplate supports three main functions:
    - ADD: Adds an html document to the template. The html is combined with any html that has been added
        to the template already. Content that is different in the new html is marked as unstable. All html added
        to a template is assumed to be different variations of the same page.
    - MATCH: Matches an html document to the template. Content marked as unstable in the template is allowed to be
        different. Content that is not marked as unstable must match.
    - UPDATE: This is meant to be called when some part of the html has changed; for example, if the url has not
        changed but we know something on the page has changed. When we update the tree, all unstable content is
        kept as unstable, but other content is updated to the new html. The purpose is to quickly create a template
        that is appropriate to the new content.
    """
    # When an attribute or text can have multiple values, use this separator.
    VALUES_SEPARATOR = u"||"
    # Special attributes added by the template.
    SPECIAL_ATTRIBUTES = {"unstable_attributes", "unstable_text", "unstable_element"}
    # When matching, only pay attention to the following attributes. (Match all attributes if None.)
    # We may not want to compare all attributes when determining if two doms match.
    # If some invisible attribute changes, do we really want that to be a different state?
    # For now we are just matching against demod_reachable to approximate the behavior of the old comparator pipeline.
    # Please note: To match all attributes, set this to None (a little counter-intuitive). To match
    #   no attributes, set this to empty set.
    ATTRIBUTES_TO_MATCH = {"demod_reachable"}

    # Strip certain things out of the dom. See _prepare_tree. This cleans up the template for readability but
    #   will slow down performance a little to run the regex.
    res_to_strip = {
        "demod_(?!reachable).+?=\".+?\"",   # Take out any demod attributes except demod_reachable.
        "demodocus-\d+",                    # Take out any demod- classes.
    }
    replace_all_re = re.compile(f"({')|('.join(res_to_strip)})", re.UNICODE)

    def __init__(self, *args):
        """Creates a template by comparing the lxml trees.

        Args:
            args: any number of html dom strings.
        """
        self._htmlstrings = set()           # All the htmlstrings that have been added to this template
        self._trees = list()                # All the trees that have been added to this template
        self._full_tree = None              # A tree containing all content from all of the trees, with annotation.
        self._unstable_elements = None      # A set of elements from the full tree that vary throughout the trees
        self._unstable_xpaths = None        # xpaths to the unstable elements

        for htmlstring in args:
            self.add_html(htmlstring)

    @classmethod
    def test_files(cls, template_file, dom_file):
        """For debugging, loads a template from file and loads a dom from file and compares them."""
        template = HtmlTemplate()
        with open(template_file, 'r', encoding='utf-8') as f:
            tree = f.read()
        template._full_tree = lxml.html.document_fromstring(tree)
        with open(dom_file, 'r', encoding='utf-8') as f:
            dom = f.read()
        explanation = {}
        result = template.matches_html(dom, explanation=explanation)
        if result:
            print("Dom matches.")
        else:
            print("Dom does not match.")
            for key, val in explanation.items():
                print(f"{key}: {val}")

    def __eq__(self, other):
        # If we want to optimize:
        # make sure the stable trees have attributes alphabetized, then just compare the strings.
        return self.matches_template(other)

    def __str__(self):
        return etree.tostring(self._full_tree, encoding='unicode')

    def xpath(self, path):
        return self._full_tree.xpath(path)

    # -- Functions for adding content to the template --
    #
    def add_html(self, htmlstring):
        """Adds a new html string to the template
        
        Args:
            htmlstring: a string of html
        """
        if htmlstring in self._htmlstrings:
            return  # Already added!
        self._htmlstrings.add(htmlstring)
        tree = self._prepare_tree(htmlstring)
        self.add_tree(tree)
    
    def add_template(self, template):
        """Adds a new template into this template

        Args:
            template: another HtmlTemplate
        """
        self._htmlstrings |= template._htmlstrings
        self.add_tree(template._full_tree)

    def add_tree(self, tree):
        """Adds a new lxml tree to the template

        Args:
            tree: a lxml tree (starting with html element)
        """
        self._trees.append(tree)
        if len(self._trees) == 1:
            self._full_tree = tree
        elif etree.tostring(tree) == etree.tostring(self._full_tree):
            return
        else:
            self._full_tree = self._get_merged_tree(self._full_tree, tree)
            # Make sure the template is still a document like we expect.
            self._assert_html_tree(self._full_tree)
            # # If most of the tree is unstable, something probably went wrong.
            # unstable_body_children = {c for c in self._full_tree.body if "unstable_element" in c.attrib}
            # if len(unstable_body_children)/len(self._full_tree.body) > .8:
            #     logger.warning("Most of the tree is unstable. Was there a popup or problem loading?")
            self._mark_dirty()  # Have to recompute the unstable elements.

    def _mark_dirty(self):
        # The template has changed so these cached values will need to be recalculated.
        self._unstable_elements = None
        self._unstable_xpaths = None
    # --

    # -- Functions for matching content to the template --
    #
    def matches_html(self, htmlstring, explanation=None):
        """Determines if html is compatible with this template.

        Args:
            html: a string of html
            explanation: Dictionary. If present, gets populated with some explanation of element matches.

        Returns:
            True if html can be accommodated without adding any instability.
        """
        tree = self._prepare_tree(htmlstring)
        return self.matches_tree(tree, explanation)

    def matches_template(self, other, explanation=None):
        """Determines if two templates are compatible.

        Args:
            other: a HtmlTemplate
            explanation: Dictionary. If present, gets populated with some explanation of element matches.

        Returns:
            True if the templates can be combined without adding any instability.
        """
        result = self.matches_tree(other._full_tree, explanation)
        return result

    def matches_tree(self, tree, explanation=None):
        """Determines if the lxml tree is compatible with this template.

        Args:
            tree: a lxml tree; can be a marked up tree from another HtmlTemplate
            explanation: Dictionary. If present, gets populated with some explanation of element matches.

        Returns:
            True if the tree can be accommodated without adding any instability.
        """
        result = self._match_trees(self._full_tree, tree, explanation)
        return result is None
    # --

    def get_updated_template(self, htmlstring):
        """Modifies the template to apply to the new htmlstring. If content is
        already marked as unstable, that is not changed. If content is currently
        was marked as stable, it is overwritten htmlstring's content. The purpose
        of this function is so that, if a page's content has changed slightly to
        a new state, we can estimate its template based on the previous state's
        template. Otherwise we would have to visit each new state multiple times.
        The function calls itself recursively on children.

        Args:
            htmlstring: a dom to use to update the existing template

        Returns:
            updated template
        """
        if htmlstring in self._htmlstrings:
            return self  # Already added! We can just return this.
        tree = self._prepare_tree(htmlstring)
        updated_tree = self._get_merged_tree(self._full_tree, tree, overwrite=True)
        new_template = HtmlTemplate()
        new_template._trees.append(self._full_tree)
        new_template._trees.append(tree)
        new_template._full_tree = updated_tree
        self._assert_html_tree(new_template._full_tree)
        return new_template

    # -- Functions for understanding the template's structure --
    #
    def is_stable(self):
        """is_stable returns True if this template has no unstable elements."""
        self.get_unstable_elements()
        return self._unstable_elements is None or len(self._unstable_elements) == 0

    def get_unstable_elements(self):
        if self._unstable_elements is None:
            self._unstable_elements = self._get_unstable_elements_from_template_tree(self._full_tree)
        return self._unstable_elements

    def get_unstable_xpaths(self):
        """Returns xpaths for elements that are marked as unstable in the template."""
        # If something has changed we need to recalculate the cached value.
        if self._unstable_xpaths is None:
            self.get_unstable_elements()
            roottree = self._full_tree.getroottree()
            self._unstable_xpaths = {roottree.getpath(el) for el in self._unstable_elements}
        return self._unstable_xpaths

    @classmethod
    def _get_xpath(cls, el):
        """Returns xpath for a particular element."""
        return el.getroottree().getpath(el)

    @classmethod
    def _get_unstable_elements_from_template_tree(cls, template_tree):
        return set(template_tree.xpath("//*[@unstable_attributes|@unstable_text|@unstable_element]"))
    # --

    # -- Functions for processing strings into trees --
    #
    @classmethod
    def _prepare_tree(cls, tree):
        """If tree is a string, converts it to a lxml tree so that it can be added to the template."""
        if isinstance(tree, str):
            tree = tree.replace("\n", "").replace("\t", "")
            tree = cls.replace_all_re.sub("", tree)
            # If there's no body tag add one.
            if tree.find("<body") == -1:
                tree = "<body>" + tree + "</body>"
            if tree.find("<html") == -1:
                tree = "<html>" + tree + "</html>"
            tree = clean_html(tree)
            tree = lxml.html.document_fromstring(tree)
            # Make sure we made the tree correctly.
            cls._assert_html_tree(tree)
        return tree

    @classmethod
    def _assert_html_tree(cls, tree):
        # Asserts if this tree has an unexpected structure like too many nested html tags.
        assert tree.getroottree().getpath(tree) == "/html"
    # --

    # -- Actual logic for combining and matching trees below --
    #
    @classmethod
    def _match_trees(cls, lel1, lel2, explanation=None):
        """Compares two lxml trees and returns as soon as an incompatibility is found.
        The function calls itself recursively on lel1 and lel2's children.

        Args:
            lel1: a lxml tree; can be a marked up tree from a HtmlTemplate
            lel2: a lxml tree; can be a marked up tree from a HtmlTemplate
            explanation: Dictionary. If present gets populated with some explanation of element matches.

        Returns:
            The first different element that was found. Returns (d1, d2) where d1 is the element in lel1 and d2
            is the element in lel2. If the element does not exist in one or the other, one of the return values is None.
            If there are no differences, this will return a single value None.
        """
        x1 = cls._get_xpath(lel1)
        x2 = cls._get_xpath(lel2)

        if etree.tostring(lel1) == etree.tostring(lel2):
            # The two trees are exactly the same.
            if explanation is not None:
                explanation[(x1, x2)] = "exact match"
            return None  # No differences

        # If the tag isn't the same, they don't match.
        if lel1.tag != lel2.tag:
            if explanation is not None:
                explanation[(x1, x2)] = f"Tag 1 {lel1.tag} does not match tag 2 {lel2.tag}"
            return lel1, lel2

        # If the elements are both html or body, no need to check attributes or text. Skip straight to the children.
        if lel1.tag != "html" and lel1.tag != "body":

            # -- Check attributes --
            unstable_attributes_in_lel1 = cls._get_unstable_attributes_for_element(lel1)
            unstable_attributes_in_lel2 = cls._get_unstable_attributes_for_element(lel2)
            unstable_attributes = unstable_attributes_in_lel1 | unstable_attributes_in_lel2

            # Remove the "special" attributes (the ones added by the template).
            lel1_attributes = set(lel1.attrib) - cls.SPECIAL_ATTRIBUTES
            lel2_attributes = set(lel2.attrib) - cls.SPECIAL_ATTRIBUTES
            all_attributes = lel1_attributes | lel2_attributes
            if cls.ATTRIBUTES_TO_MATCH is not None:
                all_attributes &= cls.ATTRIBUTES_TO_MATCH
            for key in all_attributes - unstable_attributes - {"class"}:
                if (key in lel1_attributes) != (key in lel2_attributes):
                    if explanation is not None:
                        explanation[(x1, x2)] = f"{key} exists for one but not the other."
                    return lel1, lel2
                if lel1.attrib[key] != lel2.attrib[key]:
                    if explanation is not None:
                        explanation[(x1, x2)] = f"{key} is {lel1.attrib[key]} in lel1 but {lel2.attrib[key]} in lel2."
                    return lel1, lel2

            # Match the classes separately.
            # We may not want to compare classes, as this results in more states than we need.
            # For instance, on irs.gov it results in a separate state when each menu item has focus.
            if cls.ATTRIBUTES_TO_MATCH is None or "class" in cls.ATTRIBUTES_TO_MATCH:
                if "class" not in unstable_attributes:
                    different_classes = set(lel1.classes).symmetric_difference(set(lel2.classes))
                    if len(different_classes) > 0:
                        if explanation is not None:
                            explanation[(x1, x2)] = f"different classes: {different_classes}"
                        return lel1, lel2

            # -- Check text --
            unstable_text = "unstable_text" in lel1.attrib or "unstable_text" in lel2.attrib
            if not unstable_text and lel1.text != lel2.text:
                if explanation is not None:
                    explanation[(x1, x2)] = f"different text: {lel1.text} vs {lel2.text}"
                return lel1, lel2

        # If this element is unreachable and matched so far, don't worry about checking the children.
        if ("demod_reachable" in lel1.attrib and lel1.attrib["demod_reachable"] == "false") or \
           ("demod_reachable" in lel2.attrib and lel2.attrib["demod_reachable"] == "false"):
            if explanation is not None:
                explanation[(x1, x2)] = "match unreachable"
            return None

        # -- Check the children --
        # Ideally there should be a one-to-one correspondence between children. We step one by one through each
        #   child list recursively trying to match the children.
        # Watch out!: cnn.com orders some children randomly! For instance, batBeacon and kxhead will appear in both
        #   versions of the page but in different positions. These will be marked "unstable_element" in the template.
        # When we fail to match two children at the same index and one of them is unstable, we can advance one anyway,
        #   adding it to an "unmatched child" list. Perhaps some other element will match them down the line.
        def match_el_to_list_and_remove(el, els_list):
            # If el matches an item in els_list, removes that item from the list and returns True.
            # Go backwards so we'll match the most recently added child first.
            found_match = False
            if len(els_list) > 0:
                subindex = len(els_list) - 1
                while subindex >= 0:
                    child_diff = cls._match_trees(els_list[subindex], el)
                    if child_diff is None:
                        found_match = True
                        break
                    subindex -= 1
                if found_match:
                    # The element matched an item from the list. Remove that item from the list.
                    del els_list[subindex]
            return found_match
        # Go through the children one by one trying to match them to one another.
        index1 = index2 = prev_index1 = prev_index2 = 0
        unmatched_children1 = list()
        unmatched_children2 = list()
        while index1 < len(lel1) and index2 < len(lel2):
            c1 = lel1[index1]
            c2 = lel2[index2]
            # First try to match the child in lel1 to the child in the corresponding position in lel2.
            child_explanation = None if explanation is None else {}
            child_diff = cls._match_trees(c1, c2, child_explanation)
            if child_diff is None:
                # The child matches. Move on to the next.
                prev_index1 = index1
                prev_index2 = index2
                index1 += 1
                index2 += 1
                continue
            elif explanation is not None:
                # Child does not match. Add the explanation.
                explanation.update(child_explanation)
            # That didn't work, so let's try matching the elements to any unmatched children.
            # If one of the children finds a match, advance that child index
            #   and restart the loop with the new children.
            # Check against prev_index to make sure this index has advanced. Otherwise no need
            #   to do this again.
            if index2 > prev_index2 and match_el_to_list_and_remove(c2, unmatched_children1):
                prev_index1 = index1
                prev_index2 = index2
                index2 += 1
                continue
            if index1 > prev_index1 and match_el_to_list_and_remove(c1, unmatched_children2):
                prev_index1 = index1
                prev_index2 = index2
                index1 += 1
                continue
            prev_index1 = index1
            prev_index2 = index2

            # If it is marked unstable, let's add the child to a "unmatched_children" list.
            # An unmatched child may end up matching a child from the other element down the line, in which case
            #   it will be combined with that child in the final result.
            # If we are overwriting, when we're all done, any remaining unmatched children from lel1 that are
            #   not marked unstable will be removed.
            child1_unstable = "unstable_element" in c1.attrib
            child2_unstable = "unstable_element" in c2.attrib
            # If one index is lagging behind, skip that one to catch up.
            if index1 < index2 and child1_unstable:
                unmatched_children1.append(c1)
                index1 += 1
            elif index1 > index2 and child2_unstable:
                unmatched_children2.append(c2)
                index2 += 1
            # If there are more children in one list than the other, skip the child in the bigger list.
            elif len(lel1) < len(lel2) and child2_unstable:
                unmatched_children2.append(c2)
                index2 += 1
            # Otherwise skip whichever child can be skipped.
            elif child1_unstable:
                unmatched_children1.append(c1)
                index1 += 1
            elif child2_unstable:
                unmatched_children2.append(c2)
                index2 += 1
            else:
                if explanation is not None:
                    explanation[(x1, x2)] = f"unable to match children"
                return c1, c2  # We can't make the children match.

        # We've exhausted one or the other of the element lists.
        # Check the remaining children against unmatched children from the other tree.
        while index1 < len(lel1):
            c1 = lel1[index1]
            # Is the element unreachable?
            # Does the lel1 child correspond with a skipped child from lel2, or is it unstable?
            if "demod_reachable" in c1.attrib and c1.attrib["demod_reachable"] == "false" \
                    or match_el_to_list_and_remove(c1, unmatched_children2) \
                    or "unstable_element" in c1.attrib:
                index1 += 1
            else:
                # The child from lel1 didn't match anything from lel2 and couldn't be skipped.
                if explanation is not None:
                    explanation[(x1, x2)] = f"child {c1.xpath()} didn't match anything in lel2"
                return lel1[index1], None
        while index2 < len(lel2):
            c2 = lel2[index2]
            # Is the element unreachable?
            # Does the lel2 child correspond with a skipped child from lel1, or is it unstable?
            if "demod_reachable" in c2.attrib and c2.attrib["demod_reachable"] == "false" \
                    or match_el_to_list_and_remove(c2, unmatched_children1) \
                    or "unstable_element" in c2.attrib:
                index2 += 1
            else:
                # The child from lel2 didn't match anything from lel1 and couldn't be skipped.
                if explanation is not None:
                    explanation[(x1, x2)] = f"child {c2.xpath()} didn't match anything in lel1"
                return lel2[index2], None

        if explanation is not None:
            explanation[(x1, x2)] = "match"
        return None  # No differences found.

    @classmethod
    def _get_merged_tree(cls, lel1, lel2, overwrite=False):
        """Modifies the template in lel1 to apply to lel2. If content in lel1 was
        already marked as unstable, lel2 doesn't change that. If content in lel1
        was marked as stable, it is overwritten by lel2's content. The purpose
        of this function is so that, if a page's content has changed slightly to
        a new state, we can estimate its template based on the previous state's
        template. Otherwise we would have to visit each new state multiple times.
        The function calls itself recursively on lel1 and lel2's children.
        
        Args:
            lel1: a lxml tree. Best if called with a result of get_common_template.
            lel2: a lxml tree or template, presumably of different but similar content.
                For example, these could be two different states of the same url.
            updated_elements: A set of elements that changed from lel1 to lel2. Populated by this function.

        Returns:
            template: A lxml tree that includes whatever was already marked as unstable
            in either tree, plus any new content from e2.
        """
        if etree.tostring(lel1) == etree.tostring(lel2):
            return deepcopy(lel1)  # The two trees are exactly the same.

        # Here's the template tree we're building to record the match.
        el_template = lxml.html.fromstring("<html/>")
        el_template.tag = lel1.tag

        compare_result = cls._helper_initial_element_compare(lel1, lel2)
        if compare_result == -1:
            return None  # Not the same element

        # el_template is being changed by these functions.
        # Maybe in the future a return value will be useful.
        cls._helper_combine_attributes(lel1, lel2, el_template, overwrite)
        cls._helper_combine_text(lel1, lel2, el_template, overwrite)
        cls._helper_combine_children(lel1, lel2, el_template, overwrite)
        return el_template

    # -- Helper functions used by _get_merged_tree --
    #
    @classmethod
    def _helper_initial_element_compare(cls, lel1, lel2):  # TODO: lel?
        """Does some initial checks on lel1 and lel2, which are from two
        different doms, to decide if they correspond to one another.

        Args:
            lel1, lel2: elements from two different lxml trees / templates

        Returns:
            Integer value. 1 if the elements are the same, -1 if the
            elements are different, or 0 for no result.
        """
        # TODO: Can return a score instead of 1/-1?
        # If the tag isn't the same, they don't match.
        if lel1.tag != lel2.tag:
            return -1
        # If the elements are both html or body, this should be an automatic match.
        # Should any other unique tags go here? We think no.
        if lel1.tag == lel2.tag == "html" or lel1.tag == lel2.tag == "body":
            return 1

        # If the elements have matching id's, they are the same element.
        # If they have different id's, are they different elements?
        # Watch out!: Cnn.com delays assigning id's, so the fact that lel1 has an id
        #   and lel2 does not is not a sure sign that they are different.
        # Watch out!: Cnn.com varies its id's. For instance, the same
        #   element might be called audio-player-wrapper-11111 on one load,
        #   and then audio-player-wrapper-12345 on the next load. So having different
        #   id's is not a sure sign that they are different.
        if 'id' in lel1.attrib and 'id' in lel2.attrib and lel1.attrib['id'] == lel2.attrib['id']:
            return 1

        # -- Check classes and attributes. --
        # Watch out!: Cnn.com delays assigning some attributes and classes, so the fact that
        #   elements have different attributes or classes is not a sure sign that they are different.
        # If the two elements have a class that is unique to them, that is a good
        #   sign that they are the same.
        shared_classes = set(lel1.classes) & set(lel2.classes)
        for clas in shared_classes:
            # This class only appears once in tree 1 and once in tree 2, so only in these two elements. That's
            #   a good indication that they are the same element.
            # If this fails, the element hasn't yet been added to a body for some reason.
            try:
                if len(lel1.body.getparent().find_class(clas)) == 1 and len(lel2.body.getparent().find_class(clas)) == 1:
                    return 1
            except Exception:
                # Do nothing for now, quickest fix.
                pass

        # If the two elements have an attribute that is unique to them, that is a good
        #   sign that they are the same.
        shared_attributes = set(lel1.attrib.keys()) & set(lel2.attrib.keys())
        for att in shared_attributes:
            if ":" in att:
                # Don't know how to handle namespaces in attributes.
                pass
            elif len(lel1.xpath(f"//*[@{att}]")) == 1 and len(lel2.xpath(f"//*[@{att}]")) == 1:
                # This attribute only appears once in tree 1 and once in tree 2, so only in these two elements.
                #   That's a good indication that they are the same element.
                return 1
            elif lel1.attrib[att] == lel2.attrib[att] \
                and len(lel1.xpath(f"""//*[@{att}="{lel1.attrib[att]}"]""")) == 1 and len(lel2.xpath(f"""//*[@{att}="{lel1.attrib[att]}"]""")) == 1:
                # This attribute/value pair only appears once in tree 1 and once in tree 2, so only in these two elements.
                #   That's a good indication that they are the same element.
                return 1

        # 08-19-2020 Commented this out, not true for the image carousel on webbcountytx.gov; an element
        #   can either be class="active" or have no class if it is not active. Leaving the code here
        #   in case we move to a scoring-based system in the future.
            # If one element has a class attribute and the other doesn't, that's a pretty good sign that
            #   they are different elements.
            # if ("class" in lel1.attrib) != ("class" in lel2.attrib):
            #     return -1

        # If the elements have classes but no classes in common, that is a good sign
        #   that they are different.
        if len(lel1.classes) > 0 and len(lel2.classes) > 0 and len(shared_classes) == 0:
            return -1

        return 0

    @classmethod
    def _helper_combine_attributes(cls, lel1, lel2, el_result, overwrite=False):
        """Combines attributes from lel1 and lel2.

        Args:
            lel1, lel2: elements from two different lxml trees / templates
            el_result: the element that is serving as the combination result of lel1 and lel2
            overwrite: If true, any incompatibilities will be resolved by taking from lel2. If false,
                incompatibilities will be resolved by marking the attribute as unstable.
        """
        unstable_attributes_in_lel1 = cls._get_unstable_attributes_for_element(lel1)
        unstable_attributes_in_lel2 = cls._get_unstable_attributes_for_element(lel2)
        unstable_attributes = unstable_attributes_in_lel1 | unstable_attributes_in_lel2

        # Handle the class attribute in a special way. (Union all the classes into one set.)
        lel1_classes = set(lel1.classes)
        lel2_classes = set(lel2.classes)
        if lel1_classes != lel2_classes:
            if not overwrite or "class" in unstable_attributes_in_lel1 or "class" in unstable_attributes_in_lel2:
                # If we're not overwriting, or we are overwriting but this attribute is already unstable,
                #   we should combine the values and mark it unstable.
                # For the future: Think about detecting the commonalities in the values and representing those somehow.
                #   For instance, if id="component-245-1||component-354-1", perhaps we can expect this id to always
                #   be "component-\d{3}-1".
                el_result.classes.update(lel1_classes | lel2_classes)
                unstable_attributes.add("class")
            else:
                # We are overwriting and this is not an unstable attribute in lel2, so just overwrite from lel2.
                el_result.classes = lel2.classes
        else:
            # The classes are the same, just copy from one or the other.
            el_result.classes = lel2.classes

        # Other attributes besides class.
        # Loop through all the attributes in either element and combine their values.
        # Remove the "special" attributes (the ones added by the template).
        for key in (set(lel1.attrib) | set(lel2.attrib)) - cls.SPECIAL_ATTRIBUTES - {"class"}:
            # Pull out the values into sets in case these are already templates.
            values1 = set(lel1.attrib[key].split(cls.VALUES_SEPARATOR)) if key in lel1.attrib else set()
            values2 = set(lel2.attrib[key].split(cls.VALUES_SEPARATOR)) if key in lel2.attrib else set()
            if values1 != values2:
                if not overwrite or key in unstable_attributes_in_lel1 or key in unstable_attributes_in_lel2:
                    # If we're not overwriting, or we are overwriting but this attribute is already unstable,
                    #   we should combine the values and mark it unstable.
                    el_result.attrib[key] = cls.VALUES_SEPARATOR.join(sorted(values1 | values2))
                    unstable_attributes.add(key)
                else:
                    # We are overwriting and this is not an unstable attribute in lel2, so just overwrite from lel2.
                    el_result.attrib[key] = cls.VALUES_SEPARATOR.join(values2)
            else:
                # The values are the same, just copy from one or the other.
                el_result.attrib[key] = lel2.attrib[key]
        # Now put the special attributes back.
        cls._set_unstable_attributes_for_element(el_result, unstable_attributes)
        if "unstable_element" in lel1.attrib or "unstable_element" in lel2.attrib:
            el_result.attrib["unstable_element"] = "true"
        if "unstable_text" in lel1.attrib or "unstable_text" in lel2.attrib:
            el_result.attrib["unstable_text"] = "true"

    @classmethod
    def _helper_combine_text(cls, lel1, lel2, el_result, overwrite=False):
        """Combines text from lel1 and lel2.

        Args:
            lel1, lel2: elements from two different lxml trees / templates
            el_result: the element that is serving as the combination result of lel1 and lel2
            overwrite: If true, any incompatibilities will be resolved by taking from lel2. If false,
                incompatibilities will be resolved by marking the text as unstable.
        """
        unstable_text_in_lel1 = "unstable_text" in lel1.attrib
        unstable_text_in_lel2 = "unstable_text" in lel2.attrib
        values1 = set(lel1.text.split(cls.VALUES_SEPARATOR)) \
            if lel1.text is not None and lel1.text.strip() != '' else set()
        values2 = set(lel2.text.split(cls.VALUES_SEPARATOR)) \
            if lel2.text is not None and lel2.text.strip() != '' else set()
        if values1 != values2:
            if not overwrite or unstable_text_in_lel1 or unstable_text_in_lel2:
                # If we're not overwriting, or we are overwriting but the text is already unstable in either element,
                # we should combine the values and mark it unstable.
                el_result.text = cls.VALUES_SEPARATOR.join(sorted(values1 | values2))
                el_result.attrib["unstable_text"] = "true"
            else:
                # We are overwriting and this is not unstable, so just overwrite from lel2.
                el_result.text = lel2.text
        else:
            # The values are the same, just copy from one or the other.
            el_result.text = lel2.text

    @classmethod
    def _helper_combine_children(cls, lel1, lel2, el_result, overwrite=False):
        """Combines children from lel1 and lel2.

        Args:
            lel1, lel2: elements from two different lxml trees / templates
            el_result: the element that is serving as the combination result of lel1 and lel2
            overwrite: If true, any incompatibilities will be resolved by taking from lel2. If false,
                incompatibilities will be resolved by marking the text as unstable.

        Returns:
            Nothing
        """
        # Ideally there should be a one-to-one correspondence between children. We step one by one through each
        #   child list recursively trying to match the children.
        # Watch out!: cnn.com orders some children randomly! For instance, batBeacon and kxhead will appear in both
        #   versions of the page but in different positions. These will be marked "unstable_element" in the template.
        # When we fail to match two children at the same index and one of them is unstable, we can advance one
        #   anyway, adding it to the result and to a "unmatched children" list.
        #   If we have unmatched children, we try to "catch up" by matching to them first before going on with the
        #   other children.
        # TODO: Sometimes a child in one tree matches multiple children in the other tree and it's hard to know
        #  which ones actually correspond. We can improve the child matching if our match functions return a score.
        def match_el_to_list_and_remove(el, els_list):
            # If el matches an item in els_list, removes that item from the list and returns the
            # matching element and the result of running the match function.
            if len(els_list) > 0:
                lel1_unstable = "unstable_element" in el.attrib \
                               or "unstable_text" in el.attrib \
                               or "unstable_attributes" in el.attrib
                child_result = None
                # Go backwards so we'll match the most recently added child first.
                subindex = len(els_list)-1
                while subindex >= 0:
                    cur_el = els_list[subindex]
                    # One of the elements must be marked unstable.
                    lel2_unstable = "unstable_element" in cur_el.attrib \
                               or "unstable_text" in cur_el.attrib \
                               or "unstable_attributes" in cur_el.attrib
                    if lel1_unstable or lel2_unstable:
                        child_result = cls._get_merged_tree(cur_el, el, overwrite)
                        if child_result is not None:
                            break
                    subindex -= 1
                if child_result is not None:
                    # The element matched an item from the list. Remove that item from the list.
                    match = els_list[subindex]
                    del els_list[subindex]
                    return match, child_result
            return None, None

        # Go through the children one by one trying to match them to one another.
        index1 = index2 = prev_index1 = prev_index2 = 0
        unmatched_children1 = list()
        unmatched_children2 = list()
        while index1 < len(lel1) and index2 < len(lel2):
            # First try to match the child in lel1 to the child in the corresponding position in lel2.
            child_result = cls._get_merged_tree(lel1[index1], lel2[index2], overwrite)
            if child_result is not None:
                # This element in lel2 matches the element in lel1. Definitely add it.
                el_result.append(child_result)
                if "unstable_element" in lel1[index1].attrib or "unstable_element" in lel2[index2].attrib:
                    child_result.attrib["unstable_element"] = "true"
                prev_index1 = index1
                prev_index2 = index2
                index1 += 1
                index2 += 1
                continue

            # That didn't work, so let's try matching the elements to any unmatched children.
            # If one of the children finds a match, advance that child index
            #   and restart the loop with the new children.
            # Check against prev_index to make sure this index has advanced. Otherwise no need
            #   to do this again.
            if index2 > prev_index2:
                skipped_match, child_result = match_el_to_list_and_remove(lel2[index2], unmatched_children1)
                if child_result is not None:
                    # Replace the child with the new result.
                    el_result.insert(el_result.index(skipped_match), child_result)
                    el_result.remove(skipped_match)
                    prev_index1 = index1
                    prev_index2 = index2
                    index2 += 1
                    continue
            if index1 > prev_index1:
                # If we've advanced within lel1, check the new child against all skipped children from lel2.
                skipped_match, child_result = match_el_to_list_and_remove(lel1[index1], unmatched_children2)
                if child_result is not None:
                    # Replace the child with the new result.
                    el_result.insert(el_result.index(skipped_match), child_result)
                    el_result.remove(skipped_match)
                    prev_index1 = index1
                    prev_index2 = index2
                    index1 += 1
                    continue
            # The children didn't match each other or any as-of-yet unmatched elements.
            prev_index1 = index1
            prev_index2 = index2
            # Let's add the child to the result and also to a "unmatched_children" list.
            # - If we are NOT overwriting, mark it unstable and add it to the result.
            # - If we are overwriting, do not mark it unstable unless it was already marked unstable.
            # An unmatched child may end up matching a child from the other element down the line, in which case
            #   it will be combined with that child in the final result.
            # If we are overwriting, when we're all done, any remaining unmatched children from lel1 that are
            #   not marked unstable will be removed.

            # If one index is lagging behind, skip that one to catch up.
            if index1 < index2:
                cchild = deepcopy(lel1[index1])
                if not overwrite:
                    cchild.attrib["unstable_element"] = "true"
                unmatched_children1.append(cchild)
                el_result.append(cchild)
                index1 += 1
            elif index1 > index2:
                cchild = deepcopy(lel2[index2])
                if not overwrite:
                    cchild.attrib["unstable_element"] = "true"
                unmatched_children2.append(cchild)
                el_result.append(cchild)
                index2 += 1
            # If there are more children in one list than the other, skip the child in the bigger list.
            elif len(lel1) < len(lel2):
                cchild = deepcopy(lel2[index2])
                if not overwrite:
                    cchild.attrib["unstable_element"] = "true"
                unmatched_children2.append(cchild)
                el_result.append(cchild)
                index2 += 1
            else:
                cchild = deepcopy(lel1[index1])
                if not overwrite:
                    cchild.attrib["unstable_element"] = "true"
                unmatched_children1.append(cchild)
                el_result.append(cchild)
                index1 += 1

        # We've exhausted one or the other of the element lists.
        # Check the remaining children against unmatched children from the other tree.
        while index1 < len(lel1):
            # Does the lel1 child correspond with an unmatched child from lel2?
            skipped_match, child_result = match_el_to_list_and_remove(lel1[index1], unmatched_children2)
            if child_result is not None:
                # Replace the child with the new result.
                el_result.insert(el_result.index(skipped_match), child_result)
                el_result.remove(skipped_match)
            elif not overwrite or "unstable_element" in lel1[index1].attrib:
                # As long as we're not overwriting we can add it and mark it unstable.
                cchild = deepcopy(lel1[index1])
                cchild.attrib["unstable_element"] = "true"
                el_result.append(cchild)
            else:
                # The child from lel1 couldn't be added. Keep checking the other children.
                pass
            index1 += 1
        while index2 < len(lel2):
            # Does the lel2 child correspond with a skipped child from lel1?
            skipped_match, child_result = match_el_to_list_and_remove(lel2[index2], unmatched_children1)
            if child_result is not None:
                # Replace the child with the new result.
                el_result.insert(el_result.index(skipped_match), child_result)
                el_result.remove(skipped_match)
            else:
                # Didn't match any skipped elements.
                cchild = deepcopy(lel2[index2])
                el_result.append(cchild)
                if not overwrite:
                    cchild.attrib["unstable_element"] = "true"
            index2 += 1

        # If we are overwriting, remove any remaining unmatched children from lel1 that are not marked unstable.
        # They should not be in the result.
        if overwrite:
            for unmatched_child in unmatched_children1:
                if "unstable_element" not in unmatched_child.attrib:
                    el_result.remove(unmatched_child)

        # Return what?

    @classmethod
    def _get_unstable_attributes_for_element(cls, el):
        return set(el.attrib["unstable_attributes"].split(" ")) \
            if "unstable_attributes" in el.attrib else set()

    @classmethod
    def _set_unstable_attributes_for_element(cls, el, atts):
        if len(atts) > 0:
            el.attrib["unstable_attributes"] = " ".join(sorted(atts))
    # --


import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', default='test',
                        help='Currently only valid value is `test`')
    parser.add_argument('templatefile',
                        help='template file to load')
    parser.add_argument('--htmlfile', default=None,
                        help='html file to test against the template')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()
    if args.command == 'test':
        if args.htmlfile is not None:
            HtmlTemplate.test_files(args.templatefile, args.htmlfile)
