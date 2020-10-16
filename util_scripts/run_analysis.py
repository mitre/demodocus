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
Script that runs the demodocus analysis on an output directory for a crawl
"""

import argparse
import importlib.util
import logging
from pathlib import Path
import sys

from demodocusfw.crawler import check_config_mode, import_config_from_spec

logger = logging.getLogger('crawler')

# Make this explicit
DEFAULT_CONFIG_MODE = 'demodocusfw.config.mode_default'


def parse_args():
    parser = argparse.ArgumentParser()

    # Should be specified in configuration; here only as convenience to
    # support testing
    parser.add_argument('output_dir', type=str,
                        help='Output file directory that already contains files'
                             ' created by the crawl')

    # Configuration file as python module name, e.g. 'localconfig.mode_mytest'.
    # Default mode is 'demodocusfw.config.mode_default'. Alternate modes should
    # start with "from demodocusfw.config.mode_default import *".
    parser.add_argument('-m', '--mode', default='default',
                        help='Alternative config module to load')
    # Debug flag will override the config if it exists. Otherwise use the config
    #  value.
    parser.add_argument('-d', '--debug', action='store_const',
                        dest='log_level', const=logging.DEBUG,
                        default=None,
                        help='Debug log output (logging at DEBUG)')
    parser.add_argument('-v', '--verbose', action='store_const',
                        dest='log_level', const=logging.INFO,
                        help='Verbose log output (logging at INFO)')
    args = parser.parse_args()

    return args


def init_config(output_dir, mode):
    # Load in current config
    logger.debug(f'Loading config mode: {mode}')
    if mode == 'default':
        mode = DEFAULT_CONFIG_MODE
        config_spec = importlib.util.find_spec(mode)
    else:
        try:
            config_spec = check_config_mode(mode)
        except Exception as e:
            logger.error(e)
            sys.exit(f'Unable to load configuration mode: {mode}')
    config = import_config_from_spec(config_spec)

    # Load in previous config, and throw warning if they aren't the same
    prev_cfg_fpath = Path(output_dir) / "crawl_config.txt"
    with open(prev_cfg_fpath) as fp:
        first_line = fp.readline()

    # A mode was specified
    if "--mode" in first_line:
        prev_cfg_mode = first_line.split("--mode")[-1][4:].split("'")[0]
    else:
        prev_cfg_mode = DEFAULT_CONFIG_MODE

    # Neither are contained in the either
    if not (mode in prev_cfg_mode or prev_cfg_mode in mode):
        logger.warning("Configuration mode specified doesn't match the previous"
                       " configuration mode used to generate the 'output_dir'."
                       f"\n\tPrevious config mode:\n\t\t{prev_cfg_mode}\n\t"
                       f"Specified config mode:\n\t\t{mode}")

    return config


if __name__ == '__main__':

    args = parse_args()

    config = init_config(args.output_dir, args.mode)

    if args.log_level is not None:
        config.LOG_LEVEL = args.log_level

    # Format output filename from the output_dir, and quit if it doesn't exist
    base_path = Path(args.output_dir)
    fname = base_path / "full_graph.gml"
    if not fname.exists():
        sys.exit(f'No file exists at the specified directory: {fname}')

    # Call the analyzer in the config
    analyzer = config.ANALYZER_CLASS(str(fname), config)
    analyzer.analyze()
