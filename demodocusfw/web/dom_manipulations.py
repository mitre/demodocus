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

import re

# How to mark the "reachable" attribute in the javascript.
REACHABLE_ATT_NAME = "demod_reachable"

# Various regexes for identifying things in the dom.
RE_COMMENTS = re.compile(r"\<\!\-\-.*?\-\-\>")
RE_HTML = re.compile(r"\<html(\s.*?)?\>", flags=re.DOTALL | re.MULTILINE)
RE_HEAD = re.compile(r"\<head(\s.*?)?\>", flags=re.DOTALL | re.MULTILINE)
RE_BODY = re.compile(r"\<body(\s.*?)?\>", flags=re.DOTALL | re.MULTILINE)
RE_BODY_CLOSE = re.compile(r"\</body\>")
RE_HTML_CLOSE = re.compile(r"\</html\>")
RE_BLANK_LINE = re.compile(r"(\r*\n\r*){2,}")

RE_DEMODOCUS_IGNORE = re.compile(
    r"\<(?P<tag>\w+)[^\>]*?demodocus_ignore.*?\>.*?\</(?P=tag)\>",
    re.UNICODE | re.IGNORECASE | re.DOTALL,
)

"""
This file contains JavaScript functions as well as helper code for injecting them into a webpage.
"""


def strip_comments(content):
    """Removes all html comments from content."""
    return RE_COMMENTS.sub(content, "")


def insert_before(content, regex, content_to_insert):
    """ Inserts content_to_insert into content immediately before regex. 

    Args:
        content: Existing string.
        regex: String identifier indicating where string needs to be inserted.
        content_to_insert: String to be inserted into content.

    Returns:
        New string with content_to_insert inserted into content directly before regex,
        or None if regex was not found.
    """
    match = regex.search(content)
    if match is not None:
        insert_index = match.start()
        content = content[:insert_index] + content_to_insert + content[insert_index:]
    return None if match is None else content


def insert_after(content, regex, content_to_insert):
    """ Inserts content_to_insert into content immediately after regex. 

    Args:
        content: Existing string.
        regex: String identifier indicating where string needs to be inserted.
        content_to_insert: String to be inserted into content.

    Returns:
        New string with content_to_insert inserted into content directly after regex,
        or None if regex was not found.
    """
    match = regex.search(content)
    if match is not None:
        insert_index = match.end()
        content = content[:insert_index] + content_to_insert + content[insert_index:]
    return None if match is None else content


# When Demodocus injects JavaScript, it will use the demodocus_ignore attribute in the script tag.
# When it examines the page, it will know to ignore / strip out any blocks with this attribute.
js_start = r"""<script demodocus_ignore="true">"""
js_end = r"""</script>"""

# We store all of our javascript in js files for ease in editing, but use it as strings within python

# Get all of the javascript from other files

# This one is a bit hacky since we need to set a global variable for the function,
# we just prepend it to the string
calculate_reachable_filename = "./demodocusfw/web/js/calculate_reachable.js"
with open(calculate_reachable_filename) as f:
    js_calculate_reachable = f"""var REACHABLE_ATT_NAME = "{REACHABLE_ATT_NAME}";""" + f.read()

freeze_element_data_filename = "./demodocusfw/web/js/freeze_element_data.js"
with open(freeze_element_data_filename) as f:
    js_freeze_element_data = f.read()

track_event_listeners_filename = "./demodocusfw/web/js/track_event_listeners.js"
with open(track_event_listeners_filename) as f:
    js_track_event_listeners = f.read()

get_xpath_filename = "./demodocusfw/web/js/get_xpath.js"
with open(get_xpath_filename) as f:
    js_get_xpath = f.read()

check_attributes_filename = "./demodocusfw/web/js/check_attributes.js"
with open(check_attributes_filename) as f:
    js_check_attributes = f.read()

check_css_filename = "./demodocusfw/web/js/check_css.js"
with open(check_css_filename) as f:
    js_check_css = f.read()

get_computed_outline_filename = "./demodocusfw/web/js/get_computed_outline.js"
with open(get_computed_outline_filename) as f:
    js_get_computed_outline = f.read()

focus_first_tabbable_filename = "./demodocusfw/web/js/focus_first_tabbable.js"
with open(focus_first_tabbable_filename) as f:
    js_focus_first_tabbable = f.read()


def manage_event_listeners(source):
    """ Injects JavaScript for tracking event listeners into the page source.
    This should be called before the source is written to the browser.
    """
    # Place javascript right under the head tag.
    # If there's no head tag, put it right under the body tag.


    source = insert_after(
        source, RE_HEAD, js_start + js_get_xpath + js_track_event_listeners + js_end
    ) or insert_after(
        source, RE_BODY, js_start + js_get_xpath + js_track_event_listeners + js_end
    )

    source = insert_before(
        source, RE_HTML_CLOSE, js_start + js_check_attributes + js_check_css + js_end
    ) or insert_before(
        source, RE_BODY_CLOSE, js_start + js_check_attributes + js_check_css + js_end
    )

    # Remove extra newlines before returning.
    return collapse_newlines(source)


def strip_demodocus_ignore(source):
    """ Removes any tags from the page source with demodocus_ignore=true"""
    source = RE_DEMODOCUS_IGNORE.sub("", source)
    return source


re_newlines = re.compile("[\n\r]+")


def collapse_newlines(source):
    source = re_newlines.sub("\n", source)
    return source
