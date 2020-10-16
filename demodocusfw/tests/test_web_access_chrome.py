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

import logging
import os
from sys import stdout
import unittest

from .config import mode_test as config
from demodocusfw.controller import Controller
from demodocusfw.utils import DemodocusTemporaryDirectory, set_up_logging
from demodocusfw.web.server import ThreadedHTTPServer
from demodocusfw.web.web_access import ChromeWebAccess


class TestWebAccessChrome(unittest.TestCase):

    url_template = 'http://{}:{}/demodocusfw/tests/sandbox/{}/example.html'

    @classmethod
    def setUpClass(cls):
        set_up_logging(logging.INFO)
        # Set up server to serve up the examples.
        cls._server = ThreadedHTTPServer('localhost', 0)
        cls.server_ip, cls.server_port = cls._server.server.server_address
        print('server_ip: {}'.format(cls.server_ip))
        print('server_port: {}'.format(cls.server_port))
        cls._server.start()

    @classmethod
    def tearDownClass(cls):
        cls._server.stop()

    def setUp(self):
        stdout.write('{}\n'.format(self._testMethodName))
        stdout.flush()

    def format_url(self, path):
        return self.url_template.format(self.server_ip, self.server_port, path)

    def test_chrome_output_data_dir(self):
        # Test output dir is created and destroyed as expected
        web_access = ChromeWebAccess(config)
        web_access._create_driver(config)

        temp_dir_name = web_access.get_user_data_dir_name()
        self.assertTrue(os.path.isdir(temp_dir_name))

        # Delete chrome driver access, should delete folder
        web_access.shutdown()

        self.assertFalse(os.path.isdir(temp_dir_name))

    # Seems to take too long to delete directories
    def test_chrome_output_data_dir_multiple(self):
        # Test multiple chrome drivers can operate at the same time
        web_access = []
        temp_names = []
        for i in range(4):
            web_access.append(ChromeWebAccess(config))
            web_access[i]._create_driver(config)
            temp_names.append(web_access[i].get_user_data_dir_name())

        self.assertTrue(os.path.isdir(temp_names[0]) and \
            os.path.isdir(temp_names[1]) and \
                os.path.isdir(temp_names[2]) and \
                    os.path.isdir(temp_names[3]))

        for access in web_access:
            access.shutdown()

        self.assertFalse(os.path.isdir(temp_names[0]) or \
            os.path.isdir(temp_names[1]) or \
                os.path.isdir(temp_names[2]) or \
                    os.path.isdir(temp_names[3]))

    def test_chrome_output_data_dir_controller(self):
        # We need to the controller to go out of
        config.MULTI = False
        config.NUM_THREADS = 1
        config.OUTPUT_DIR = DemodocusTemporaryDirectory()
        controller = Controller(ChromeWebAccess, config)

        controller.access.load(self.format_url('test/list_inaccessible_1')) # Need to run to have chrome driver initialise

        temp_dir_name = controller.access.get_user_data_dir_name()
        self.assertTrue(os.path.isdir(temp_dir_name))

        controller.stop()

        self.assertFalse(os.path.isdir(temp_dir_name))

    def test_chrome_output_data_dir_driver_inactive(self):
        # Tests for no error if web access isn't used before it is destroyed
        self.web_access = ChromeWebAccess(config)


if __name__ == '__main__':
    unittest.main()
