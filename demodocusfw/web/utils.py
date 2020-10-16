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
import urllib

from lxml.html.clean import Cleaner

from demodocusfw.utils import get_output_path
from demodocusfw.web.server import ThreadedHTTPServer

def serve_output_folder(config):
    """Sets up a web server in the config's output directory.
    This function updates the config with the server ip and port"""
    # Make sure the output folder exists.
    output_dir = get_output_path(config)
    # Set up an ad hoc server to serve pages from the output folder.
    # Save the ip and port in the config.
    server = ThreadedHTTPServer('localhost', 0, path=output_dir)
    config.server_ip, config.server_port = server.server.server_address
    server.start()
    return server


def urls_equal(url1, url2, path=True, query=False, fragment=False):
    """Compares two urls. """
    # urlparse creates a 6-tuple with the following breakdown: scheme://netloc/path;parameters?query#fragment
    # Make sure the domain and the path are the same.
    url1 = urllib.parse.urlparse(url1)
    url2 = urllib.parse.urlparse(url2)
    if path and (url1[1] != url2[1] or url1[2] != url2[2]):
        return False
    if query and (url1[3] != url2[3] or url1[4] != url2[4]):
        return False
    if fragment and (url1[5] != url2[5]):
        return False
    return True


# A cleaner for stripping html before processing.
# Strip comments, styles, and scripts.
# Since the cleaner defaults a bunch of other things to true, we need to set them back to false.
# Also get rid of time elements since we expect them to change.
# Get rid of twitter widgets since these are expected to change.
# Strip out `use` tags since I'm not sure how to handle namespaces in attributes.
# Remove svg tags since these are only graphical in nature and we don't analyze them.
_html_cleaner = Cleaner(comments=True, style=True, scripts=True,
                        kill_tags={'script', 'time', 'head', 'use', 'twitter-widget', 'svg'},
                        remove_unknown_tags=False, safe_attrs_only=False, annoying_tags=False,
                        page_structure=False, forms=False, links=False)


def clean_html(html):
    html = _html_cleaner.clean_html(html)
    return html
