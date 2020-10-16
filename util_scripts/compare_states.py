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
Script to manually compare two states. This is meant for debugging purposes for the
comparator pipeline. 

A typical workflow would include running a crawl on a url, seeing screenshots of multiple
states that appear identical, then running the script here to determine why the comparator
classified them as two unique states. Generally, it is assumed you will be running this
script in debug mode.

Note: That this doesn't help the case where states are incorrectly identified as matching, but
this tends to be a rarer problem.
"""

import argparse
import importlib.util
import logging
from pathlib import Path
import sys
import itertools

from demodocusfw.crawler import check_config_mode, import_config_from_spec
from demodocusfw.comparator import Comparer

logger = logging.getLogger('demodocus')

# Set highest level config with comparator pipeline defined as default
DEFAULT_CONFIG_MODE = 'demodocusfw.config.mode_accessibility'

def parse_args():
    parser = argparse.ArgumentParser()

    # Get directory of crawl. Using a standard crawl, this will likely be in
    # build/crawls/(crawl name/timestamp). 
    parser.add_argument('output_dir', type=str, help="Output file directory that already contains fileds created by the crawl")
    
    # Get the state ids to compare, we accept a list of id's that will all be pairwise compared
    parser.add_argument('state_ids', type=int, help="List of state ids for comparison. Must have length >= 2.", nargs='+')

    # Set a custom comparator pipeline
    parser.add_argument('-m', '--mode', default='default', help='Alternative config module to load')

    # Set logger to info mode
    parser.add_argument('-v', '--verbose', action='store_const', dest='log_level', const=logging.INFO, help="Verbose log output.")

    # Debug mode for logger
    parser.add_argument('-d', '--debug', action='store_const', dest='log_level', const=logging.DEBUG, help="Debug log output.")
    
    return parser.parse_args()

def init_config(mode):
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

    return config


if __name__ == '__main__':
    args = parse_args()

    if args.log_level is not None:
        logging.basicConfig(level=args.log_level, format="%(message)s")

    logger.debug("Received args: %s", args)


    config = init_config(args.mode)
    compare_pipeline = config.COMPARE_PIPELINE

    state_path = Path(args.output_dir) / 'states'
    logger.info("Looking in state path: " + str(state_path))

    results = dict()
    state_dict = dict()

    # States should have the form state-i for integers i
    # We want to compare all states pairwise
    for pair in itertools.product(args.state_ids, args.state_ids):
        if pair[0] == pair[1]: # Don't compare the same state
            continue

        logger.info("Comparing states %s and %s", pair[0], pair[1])

        for state_id in pair:
            if state_id not in state_dict:
                file_path = state_path / ('state-' + str(state_id) + '.html')
                with open(file_path, encoding="utf-8") as state_fp:
                    logger.info("Reading info from file %s", file_path)
                    state_dict[state_id] = state_fp.read()

        si_text = state_dict[pair[0]]
        sj_text = state_dict[pair[1]]
        results[(pair[0], pair[1])] = Comparer.compare(si_text, sj_text, compare_pipeline)

    print(f"Results: {results}")
