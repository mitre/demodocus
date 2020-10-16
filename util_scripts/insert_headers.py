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

import os
import argparse

from git import Repo


def parse_args():
    """Parse args for this script

    Returns:
        args: parsed command-line arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--repo-path", type=str, required=True,
                        help="Path of the git repo")
    parser.add_argument("-e", "--extension", type=str, required=True,
                        help="Extension of files to add headers to (ex: '.py')")
    args = parser.parse_args()

    return args


def write_header(fpath, header):
    """Write a header to a file, checking for shebang and encoding

    Args:
        fpath: path and filename to add header to
        header: header string in prepend to the file
    """

    with open(fpath, 'r+') as f:
        content = f.read()
        # check if there is a shebang and encoding
        if content[:45] == '#!/usr/bin/env python\n# -*- coding: utf-8 -*-':
            f.seek(46, 0)
            f.write('\n' + header + content[46:])
        # check if there is only a shebang
        elif content[:21] == '#!/usr/bin/env python':
            f.seek(22, 0)
            f.write('\n' + header + content[22:])
        # no shebang or encoding
        else:
            f.seek(0, 0)
            f.write(header + content)


if __name__ == "__main__":

    # TODO This may need to be changed if we want a different message
    # indentations here are annoying, but it'll change the header if aligned
    header_template = """
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

    # other variables to assist the gitpython commands
    header_template = '"""' + header_template + '"""\n\n'
    log_author = '--pretty=format:"%ae%x09"'
    log_date = '--format=%ai'

    # getting args and initializing repo
    args = parse_args()
    repo = Repo(args.repo_path)

    # iterate through files, appending a header to each one
    files_headered = []
    for root, dirs, files in os.walk(args.repo_path):
        for file in files:
            # TODO allow user to specify other files to ignore besides
            #  ..."__init__.py"
            if file.endswith(args.extension) \
                    and not file.endswith("__init__.py"):
                file_fpath = os.path.join(root, file)

                # get and parse author information
                authors_set = repo.git.log(log_author, file_fpath)
                authors_set = set(authors_set.replace("\t", "") \
                                  .replace('"', '').split("\n"))
                authors_set_str = str(authors_set)[1:-1].replace("'","")

                # get date created
                creation_date = repo.git.log(log_date, file_fpath) \
                    .split('\n')[-1].split(' ')[0]

                # write header to files tracked by git
                # TODO probably a better way to do this by just looping through
                # ...files tracked by our repo
                if authors_set_str != "":
                    file_header = header_template.format(authors_set_str,
                                                         creation_date)
                    write_header(file_fpath, file_header)
                    files_headered.append(file_fpath)

    print(f"Wrote custom headers to {len(files_headered)} "
          "files tracked by git:")
    for filename in files_headered:
        print(f"    {filename}")



