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

# Adapted from https://docs.python.org/3/library/http.server.html
import functools
import http.server
# import os
import threading

from demodocusfw.utils import ROOT_DIR

PORT = None

class ThreadedHTTPServer(object):
    def __init__(self, host, port, path=None,
                 request_handler=http.server.SimpleHTTPRequestHandler):
        if path is None:
            path = ROOT_DIR
        self.path = path
        # Requires >= python 3.7
        request_handler = functools.partial(request_handler, directory=str(path))
        request_handler.directory = str(path)
        self.server = http.server.HTTPServer((host, port), request_handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True

    def start(self):
        print(f"Serving {self.path} on port {self.server.server_address[1]} in thread {self.server_thread.name}")
        self.server_thread.start()

    def stop(self):
        print("Stopping server loop")
        self.server.shutdown()
        self.server.server_close()

    def __del__(self):
        self.stop()

    def __exit__(self, type, value, traceback):
        self.stop()


server = None


def start():
    global PORT, server
    # Port 0 means to select an arbitrary unused port
    HOST, PORT = "localhost", 0

    server = ThreadedHTTPServer(HOST, PORT)
    ip, PORT = server.server.server_address
    server.start()


def stop():
    global server
    server.stop()
