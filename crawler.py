#!/usr/bin/env python

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

"""
Main script for running the demodocus crawler at demodocusfw.crawler.
"""
import argparse
import fileinput
import importlib.util
import logging
from pathlib import Path
import sys

from demodocusfw.crawler import Crawler, check_config_mode, \
    import_config_from_spec

logger = logging.getLogger('crawler')

# Make this explicit
DEFAULT_CONFIG_MODE = 'demodocusfw.config.mode_accessibility_vision_users'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('entry_point', nargs='?', metavar='ep', default=None,
                        help='String to use to load or launch the initial state to crawl, like a url')
    parser.add_argument('-i', '--inputfile', nargs='?',
                        help='entry points to crawl, one per line')

    # Should be specified in configuration; here only as convenience to
    # support testing
    parser.add_argument('--output_dir', default=None,
                        help='Output file directory')

    # Configuration file as python module name, e.g. 'localconfig.mode_mytest'.
    # Default mode is 'demodocusfw.config.mode_default'. Alternate modes should
    # start with "from demodocusfw.config.mode_default import *".
    parser.add_argument('-m', '--mode', default='default',
                        help='Alternative config module to load')
    # Debug flag will override the config if it exists. Otherwise use the config value.
    parser.add_argument('-d', '--debug', action='store_const',
                        dest='log_level', const=logging.DEBUG,
                        default=None,
                        help='Debug log output (logging at DEBUG)')
    parser.add_argument('-v', '--verbose', action='store_const',
                        dest='log_level', const=logging.INFO,
                        help='Verbose log output (logging at INFO)')
    args = parser.parse_args()

    # allow args to accept new item assignments
    d = vars(args)

    # converting either url argument into a python list of url strings
    if args.entry_point is None:
        d['entry_points'] = [line.strip() for line in fileinput.input(args.inputfile)]
    else:
        d['entry_points'] = [args.entry_point]

    return args


if __name__ == '__main__':
    args = parse_args()

    logger.debug(f'Loading config mode: {args.mode}')
    if args.mode == 'default':
        config_spec = importlib.util.find_spec(DEFAULT_CONFIG_MODE)
    else:
        try:
            config_spec = check_config_mode(args.mode)
        except Exception as e:
            logger.error(e)
            sys.exit(f'Unable to load configuration mode: {args.mode}')
    config = import_config_from_spec(config_spec)

    # If these args are present on command line, override even a specified mode
    if args.output_dir is not None:
        config.OUTPUT_DIR = Path(args.output_dir)

    if args.log_level is not None:
        config.LOG_LEVEL = args.log_level

    crawler = Crawler(config=config)
    crawler.crawl_all(args.entry_points)
    del crawler
