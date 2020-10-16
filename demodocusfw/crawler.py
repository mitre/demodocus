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
Main script for controlling the demodocus crawler.
"""

import csv
import importlib.util
import logging
import os
from pathlib import Path
import shutil
import sys
from time import time

from demodocusfw.comparator import Comparer
from demodocusfw.utils import get_screenshot_dir, set_up_logging, stop_logging

logger = logging.getLogger('crawler')


class Crawler:
    """Manages many Crawl() objects and their crawls"""
    def __init__(self, config):
        self.config = config
        self.output_dir = str(config.OUTPUT_DIR)
        os.makedirs(self.output_dir, exist_ok=True)
        self.reports = config.REPORTS
        self.output_file = config.OUTPUT_FILE
        self.access_class = config.ACCESS_CLASS
        Comparer.default_pipeline = config.COMPARE_PIPELINE
        self.multi = config.MULTI
        self.num_threads = config.NUM_THREADS
        self.use_multi = self.num_threads > 1 or self.multi
        self.build_user = config.BUILD_USER
        self.crawl_users = config.CRAWL_USERS
        self.screenshots = config.SCREENSHOTS
        self.delay = config.DELAY
        self.log_level = config.LOG_LEVEL
        self.crawl = Crawl()
        self.initialized = False
        self.controller = None

        # Set up logging
        set_up_logging(config.LOG_LEVEL, Path(self.output_dir) / self.output_file, config.LOG_TO_STDOUT)

        # setting up screenshot directory
        self.screenshot_dir = get_screenshot_dir(self.config)

        # asserting that the Crawler was properly initialized
        self.initialized = True

    def crawl_all(self, entry_points):
        """
        Crawl each entry point in turn.

        Args:
            entry_points: A list of one or more resource locators or launch strings to start crawling.
        """

        assert self.initialized, '"crawler() object was not properly initialized'
        assert isinstance(entry_points, list), '"entry_points" needs to be a list of resource locator or launch strings'
        assert len(entry_points) >= 1, 'need to specify at least one entry point in "entry_points"'

        self.controller = self.access_class.make_controller(self.config)

        # write config to file; NOTE: this may need refinement
        if 'all' in self.reports \
                or 'config' in self.reports:
            config_fname = Path(self.output_dir) / 'crawl_config.txt'
            # Only write fields in config that are all uppercase
            with open(config_fname, 'w') as config_fp:
                config_fp.write(f'ARGV = {sys.argv}\n\n')
                for k in dir(self.config):
                    if k.isupper():
                        config_fp.write('{} = {}\n\n'.format(k,
                                        getattr(self.config, k, '')))

        # crawl and report only one entry point
        if len(entry_points) == 1:
            entry_point = entry_points[0]
            logger.debug('One entry point to crawl')
            entry_point_id = -1
            self.crawl = time_crawl(self.controller, entry_point, self.crawl,
                                    self.build_user, self.crawl_users,
                                    self.use_multi, entry_point_id)

        # crawl and report many entry points
        elif len(entry_points) > 1:
            entry_point_id = 0
            for entry_point in entry_points:
                logger.debug('Next entry point: {}'.format(entry_point))
                self.crawl = time_crawl(self.controller, entry_point,
                                        self.crawl, self.build_user,
                                        self.crawl_users, self.use_multi,
                                        entry_point_id)
                if self.screenshot_dir:
                    shutil.copytree(self.screenshot_dir,
                        Path(self.output_dir) / f"ep-{entry_point_id}" / "screenshots")
                    shutil.rmtree(self.screenshot_dir)
                    os.makedirs(self.screenshot_dir, exist_ok=True)
                entry_point_id += 1

                self.controller.reset_graph()

            if self.screenshot_dir:
                shutil.rmtree(self.screenshot_dir)
        else:
            logger.debug('No entry points specified for crawling')
            # Nothing to report, so stop here
            return

        # Stop controller. Will delete access/driver.
        # MultiController needs to be told to stop all threads.
        stop_logging()
        self.controller.stop()


class Crawl:
    """Contain and report out on the history of a crawl."""
    fieldnames = ['id', 'entry_point', 'duration_sec', 'num_nodes', 'num_edges',
                  'users_crawled']

    def __init__(self):
        self.history = []

    def add(self, entry_point_id, entry_point, duration_sec, num_nodes,
            num_edges, users_crawled):
        """
        Add a crawled entry point to the history of a crawler run.

        Args:
            entry_point_id: An integer indicating the index of the entry point crawled.
            entry_point: The entry point crawled.
            duration_sec: How long the crawl took in seconds.
            num_nodes: Integer count of states found at this entry point.
            num_edges: Integer count of edges found at this entry point.
            users_crawled: list of str for the users crawled up until this point
        """
        self.history.append({
            'id': entry_point_id,
            'entry_point': entry_point,
            'duration_sec': round(duration_sec, 2),
            'num_nodes': num_nodes,
            'num_edges': num_edges,
            'users_crawled': ';'.join(users_crawled)
        })

    def to_csv(self, fname):
        """
        Export the crawl history data to CSV.

        Args:
            fname: Filename to write CSV report to.
        """
        logger.debug('Writing CSV crawl data to {}'.format(fname))
        with open(fname, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            writer.writeheader()
            for crawl in self.history:
                writer.writerow(crawl)


def crawl_one(controller, entry_point, crawl, build_user, users,
              use_multi=False, pos=-1):
    """
    Crawl the state space of entry_point with options provided.
    FIXME: handle network/web errors
    TODO: consider validating entry point before starting crawl

    Args:
        controller: The controller to use for crawling this entry point.
        entry_point: The entry point to crawl.
        crawl: object that contains the crawl history
        build_user: UserModel to build the graph.
        users: List of UserModels to crawl the built graph.
        use_multi: When MultiController is used, set to True to stop pool.
        pos: Integer index of entry point in list of entry points crawled.

    Returns:
        The controller used for crawling, post-crawl.
    """
    logger.info('Crawling {}'.format(entry_point))

    t0 = time()
    if not controller.load(entry_point):
        logger.error('Failed to load entry point')
        raise Exception('Failed to load entry point')
    if len(users) == 0:
        # If no users are specified for crawling, let's just build the graph without crawling it.
        logger.warning('No valid users specified, graph will be built but not crawled.')
    # Note: always build the graph with OmniUser first.
    logger.info('Building graph w/{}'.format(build_user.get_name()))
    controller.build_graph(build_user)
    users_crawled = [build_user.get_name()]
    crawl.add(pos, entry_point, time()-t0, len(controller.graph.get_states()),
              len(controller.graph.get_edges()), users_crawled)
    if len(controller.graph.states) == 0:
        # We should have at least one state.
        logger.error("No states available, probably an error with build_graph.")
        raise Exception("No states available, probably an error with build_graph.")
    logger.info(f"Changing reporting from {controller.config.REPORTS} to "
                f"{['states', 'gml', 'metrics']}")
    controller.config.REPORTS = ['states', 'gml', 'metrics']
    report(controller, entry_point, controller.config, crawl, pos=pos)
    logger.info(f"Changing reporting from {controller.config.REPORTS} to "
                f"{['gml', 'metrics']}")
    controller.config.REPORTS = ['gml', 'metrics']

    for user in users:
        if user == users[-1]:
            logger.info(f"Changing reporting from {controller.config.REPORTS} "
                        f"to {['gml', 'analysis', 'metrics']}")
            controller.config.REPORTS = ['gml', 'analysis', 'metrics']
        logger.info('Crawling graph w/{}'.format(user.get_name()))
        controller.crawl_graph(user)
        users_crawled.append(user.get_name())
        crawl.add(pos, entry_point, time() - t0,
                  len(controller.graph.get_states()),
                  len(controller.graph.get_edges()), users_crawled)

        report(controller, entry_point, controller.config, crawl, pos=pos)

    if use_multi:
        logger.debug('Awaiting crawl(s) completion')
        controller.pool.wait_completion()

    return crawl


def report(controller, entry_point, config, crawl, pos=-1):
    """
    Write out GML, DOMs, etc. in crawl report.

    Args:
        controller: Controller used to crawl entry point.
        entry_point: resource locator or launch string for initiating the crawling.
        config: entire config stored by the Crawler object. Fields always pulled
                are BUILD_USER, CRAWL_USERS, REPORTS, OUTPUT_DIR, ANALYZER_CLASS
        crawl: object that contains the crawl history
        pos: Integer index of entry point in list of entry points crawled.
    """
    if 'all' not in config.REPORTS \
        and 'gml' not in config.REPORTS:
        logger.info('No reports requested.')
        return
    logger.info('Generating reports for {}'.format(entry_point))

    # Split reports into separate dirs if we're crawling more than one entry_point
    if pos >= 0:
        crawl_output_dir = Path(config.OUTPUT_DIR) / 'ep-{}'.format(pos)
        os.makedirs(crawl_output_dir, exist_ok=True)
    else:
        crawl_output_dir = str(config.OUTPUT_DIR)

    # Writing states to files
    if 'all' in config.REPORTS \
            or 'states' in config.REPORTS:
        state_output_dir = Path(crawl_output_dir) / 'states'
        os.makedirs(state_output_dir, exist_ok=True)
        for state in controller.graph.get_states():
            state.save(state_output_dir)

    # Writing graph to gml
    if 'all' in config.REPORTS \
            or 'gml' in config.REPORTS:
        fname = Path(crawl_output_dir) / 'full_graph.gml'
        controller.graph.to_gml(config.BUILD_USER, fname)
        if 'all' in config.REPORTS \
                or 'analysis' in config.REPORTS:
            analyzer = config.ANALYZER_CLASS(fname, config)
            analyzer.analyze()

    # Writing crawl stats to csv/json
    if 'all' in config.REPORTS \
            or 'metrics' in config.REPORTS:
        report_fname = Path(crawl_output_dir) / 'crawl.csv'
        crawl.to_csv(report_fname)


def time_crawl(controller, entry_point, crawl, build_user, users, use_multi,
               pos):
    """
    Track time spent when invoking the controller to crawl the entry point.

    Args:
        controller: The controller to use when crawling.
        entry_point: entry point to crawl.
        crawl: object that contains the crawl history
        users: Which user models are to be used for crawling.
        use_multi: Whether the MultiController is being used.
        pos: Integer index of entry point in list of entry points crawled.

    Returns:
        (controller, time spent in seconds)
    """
    crawl = crawl_one(controller, entry_point, crawl, build_user, users,
                      use_multi=use_multi, pos=pos)

    return crawl


def check_config_mode(mode):
    """
    Checks if configuration module can be imported without importing it
    Adapted from:
    https://www.blog.pythonlibrary.org/2016/05/27/python-201-an-intro-to-importlib/

    Args:
        mode: A Python module, e.g. "demodocusfw.config.mode_default"

    Returns:
        An importlib module spec ready for loading.
    """
    module_spec = importlib.util.find_spec(mode)
    if module_spec is None:
        logger.error('Configuration mode "{}" not found'.format(mode))
        return None
    return module_spec


def import_config_from_spec(module_spec):
    """
    Import the configuration via the passed in mode specification
    From same source as check_config_mode()

    Args:
        module_spec: An importlib module spec.

    Returns:
        A Python module, loaded and executed.
    """
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module
