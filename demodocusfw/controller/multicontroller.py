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

from collections import deque
from difflib import unified_diff
import logging
from pathlib import Path
from queue import Queue
import random
import threading
import time
import traceback

from demodocusfw.graph import Graph
from demodocusfw.utils import get_screenshot_dir
from demodocusfw.web.utils import serve_output_folder

logger = logging.getLogger('crawler.multicontroller')

"""
Worker/Threadpool draws from template code at:
   https://www.pythonsheets.com/notes/python-concurrency.html
   https://www.metachris.com/2016/04/python-threadpool/
"""


def state_diff(d1, d2):
    """
    Helper function. Returns a string containing the unified
    diff of two multiline strings.

    Args:
        d1: String to be compared.
        d2: String to be compared.

    Returns:
        A unified diff of the multiline strings d1 and d2.
    """
    d1_split = d1.splitlines(1)
    d2_split = d2.splitlines(1)
    return ''.join(unified_diff(d1_split, d2_split, fromfile='d1',
        tofile='d2'))


def fuzz(secs=1):
    """Forced wait to support thread debugging. Waits a random amount of
    time. Note: don't confuse this delay with `delay` arg, hence long name"""
    fuzz_delay = secs * random.random()
    logger.debug('Fuzz: {} secs'.format(fuzz_delay))
    time.sleep(fuzz_delay)


def get_screenshot(screenshot_dir, access, state_id):
    """Take a screenshot of the interface and save it to a specified directory.

    Args:
        screenshot_dir: The string representing the directory to which the screenshot will be saved.
        access: Access to the user interface for retrieving actionable elements.
        state_id: An int representing the ID of the state.
    """
    if screenshot_dir:
        screenshot_path = Path(screenshot_dir) / \
            'state-{}.png'.format(state_id)
        # Note: webdriver wants a string, not a Path
        access.capture_screenshot(str(screenshot_path))
    return


def build(entry_point, user, graph, access, state=None, delay=0,
          screenshot_dir=None):
    """Examines one state, returning a list of possible states user can reach.

    Args:
        load_string: An identifier used to specify a specific state.
        user: user (instance of UserModel) or user name as string.
        graph: graph instance that is being built.
        access: Access to the user interface for retrieving actionable elements. Defaulted to None.
        state: The starting state. Defaulted to None. This allows the load_string to be used.
        delay: Specify how long process should sleep for. Defaulted to None.
        screenshot_dir: Directory to add screenshots to. Defaulted to None.

    Returns:
        A list of possible states user can reach from a specific state."""

    states_found = []

    if state is None:
        if not access.load(entry_point):
            logger.error("Failed to load entry point.")
            return states_found
        was_added, state = graph.add_state(access.get_state_data())
        access.set_state(state)
        # This user can access the start state.
        state.set_user_path(user, [])
        if was_added:
            get_screenshot(screenshot_dir, access, state.id)

            # Generate the tab order for the state
            tab_dict, tab_els_by_index, orig_focused_xpath = access.generate_tab_order()
            state.data.tab_dict = tab_dict
            state.data.tab_els_by_index = tab_els_by_index
            state.data.orig_focused_xpath = orig_focused_xpath
    else:
        access.set_state(state)

    logger.info(f"-- Exploring state {state.id}")

    # Okay, now we should be in the desired state. Let's start searching.
    for action in access.get_actions():
        els = action.get_elements(access)
        for el in els:
            logger.debug(f"Trying {action} on {el}")
            edge_metrics = access.perform_action_on_element(user, action, el)
            # See if the new state is a stub state
            if edge_metrics.ability_score > 0.0:
                new_state_data = access.get_state_data()
                # Compare the state datas to see if it's changed.
                if new_state_data.stub or new_state_data != state.data:
                    # This state data is different than what was there before.
                    # Does it match any states we have already seen?
                    was_added, new_state = graph.add_state(new_state_data)

                    # Add the edge to the graph.
                    new_edge = graph.add_edge(state, new_state, el, action)
                    new_edge.add_data_for_user(user, edge_metrics)

                    if was_added:
                        # We have not yet seen this state.
                        # Add the state to the graph
                        logger.info(f"from {state.id} to {new_state.id} via {action} on {el} (NEW STATE)")
                        get_screenshot(screenshot_dir, access, new_state.id)
                        time.sleep(delay)
                        # Do not (re)visit stub states
                        if not new_state_data.stub:
                            states_found.append(new_state)

                            # Generate the tab order for this new state
                            tab_dict, tab_els_by_index, orig_focused_xpath = access.generate_tab_order(el.xpath)
                            new_state.data.tab_dict = tab_dict
                            new_state.data.tab_els_by_index = tab_els_by_index
                            new_state.data.orig_focused_xpath = orig_focused_xpath

                        # Remember how this user got here.
                        new_state.set_user_path(user, state.get_user_path(user)
                                                + [new_edge])
                    else:
                        logger.info(f"from {state.id} to {new_state.id} via {action} on {el}")

                    # Now put the old state back.
                    access.set_state(state)
                else:
                    access.set_state_direct(state)
    return states_found


def crawl(user, graph, build_user, access=None, start_state=None):
    """Crawl the built graph with user, attempting to reach all known states
    via all edges build_user found. FIXME: Single-threaded for now; is fast.

    Args:
        user: user (instance of UserModel) or user name as string.
        graph: Built graph.
        build_user: str denoting the name of the build user
        access: Access to the user interface for retrieving actionable elements. Defaulted to None.
        state: The starting state. Defaulted to None. This allows the graph start state to be used.
    """

    if start_state is None:
        start_state = graph.start_state

    # This user can access the start state.
    start_state.set_user_path(user, [])

    states_to_visit = deque([start_state])
    seen_states = {start_state}  # set of states
    try:
        while len(states_to_visit) > 0:
            state = states_to_visit.pop()
            logger.info("-- Crawling state {} --".format(state.id))

            for outgoing_edge in graph.get_edges_for_state(state):
                # Simulate action based on what is captured by the build_user
                edge_metrics = access.simulate_action_on_element(user,
                                                                 outgoing_edge.action,
                                                                 outgoing_edge.element,
                                                                 outgoing_edge.user_metrics[build_user])
                if edge_metrics.ability_score > 0.0:
                    # The user can follow this edge.
                    outgoing_edge.add_data_for_user(user, edge_metrics)
                    new_state = outgoing_edge.state2
                    logger.info(f"found state {new_state.id}: {outgoing_edge.action} on {outgoing_edge.element}")
                    if new_state not in seen_states:
                        seen_states.add(new_state)
                        # Remember how this user gets to this state.
                        new_state.set_user_path(user, state.get_user_path(user) + [outgoing_edge])
                        # Add this state to the queue so we can visit it later.
                        if not new_state.stub:
                            states_to_visit.appendleft(new_state)
    except Exception as e:
        # An exception happened in this thread
        logger.error(e)
        logger.debug(traceback.format_exc())
    return []


def noop(*args, **kwargs):
    """No operation. Used to activate threads to receive stop signals."""
    logger.debug('No op')
    return []


class Worker(threading.Thread):
    """Individual crawl worker, with its own web driver, to be reused."""

    def __init__(self, queue, stop_event, access_class, config):
        threading.Thread.__init__(self)
        self.queue = queue
        self.stop_event = stop_event
        self.access = access_class(config=config)
        self.daemon = True
        logger.debug('Starting new worker')
        self.start()

    def run(self):
        while not self.stop_event.is_set():
            func, args, kwargs = self.queue.get()
            # assign the thread-local access
            kwargs['access'] = self.access
            try:
                states_found = func(*args, **kwargs)
                while len(states_found) > 0:
                    # partition: continue with last, defer rest
                    # continue (last) state will proceed in this thread
                    continue_state = states_found.pop()
                    # enqueue the rest of the new states for later processing
                    if len(states_found) > 0:
                        # need independent dict to pass to avoid shared refs
                        for defer_state in states_found:
                            # Note: deep copy manually now because
                            # copy.deepcopy() will attempt to pickle our
                            # objects, which fails
                            new_kwargs = {}
                            for k, v in kwargs.items():
                                new_kwargs[k] = v
                            # ...but don't share ref to thread-local access
                            del(new_kwargs['access'])
                            new_kwargs['state'] = defer_state
                            logger.info(f"Putting state {defer_state.id} on queue.")
                            self.queue.put((func, args, new_kwargs))
                    # proceed in this thread w/last (current) new state
                    kwargs['state'] = continue_state
                    states_found = func(*args, **kwargs)
            except Exception as e:
                # An exception happened in this thread
                logger.error(e)
                logger.debug(traceback.format_exc())
            finally:
                # Mark this task as done, whether an exception happened or not
                self.queue.task_done()
        logger.debug('Received stop event')


class ThreadPool:
    """Pool of threads consuming tasks from a queue"""
    def __init__(self, access_class, config):
        # Defaults to unlimited queue size
        self.num_threads = config.NUM_THREADS
        self.access_class = access_class
        self.queue = Queue()
        self.stop_event = threading.Event()
        self.workers = []
        for _ in range(self.num_threads):
            worker = Worker(self.queue, self.stop_event, access_class, config)
            self.workers.append(worker)
        logger.debug('Initialized ThreadPool')

    def add_task(self, func, *args, **kargs):
        """Add a task to the queue

        Args:
            func: Function to be performed.
            *args: Arguments(s) to be acted on by func.
        """
        self.queue.put((func, args, kargs))

    def map(self, func, args_list):
        """Add a list of tasks to the queue

        Args:
            func: function to be performed
            args_list: A list of arguments to be acted on by func.
        """
        for args in args_list:
            self.add_task(func, args)

    def wait_completion(self):
        """Wait for completion of all the tasks in the queue"""
        self.queue.join()

    def stop(self):
        """Send stop signal to each worker
        This should only be called once we are all done building and crawling.
        """
        self.stop_event.set()
        # First fire up (hopefully) all threads
        for i in range(len(self.workers)):
            if self.workers[i].access is not None:
                self.queue.put((noop, [], {}))
        # Wait for noops to complete
        self.queue.join()
        # Explicit removal of access should kill driver procs
        for worker in self.workers:
            if worker.access is not None:
                worker.access.reset()
                worker.access.shutdown()  # This is necessary to kill the procs.
                worker.access = None


class MultiController:
    """Class that controls multiple threads in order to run multiple workers to build multiple graphs."""

    def __init__(self, access_class, config):
        self.graph = Graph()
        self.access_class = access_class
        self.delay = config.DELAY
        self.screenshot_dir = get_screenshot_dir(config)
        self.config = config
        self.crawled_users = set()
        self.entry_point = None

        # Has to be in the controller, not the WebAccess, for multi-threading.
        # (Each thread has its own access with its own memory space.)
        self._server = serve_output_folder(config)

        # Need to finish setting up the config for the server before creating web accesses
        self.pool = ThreadPool(access_class, config)

    def build_graph(self, user, entry_point=None):
        """Procedure for crawling a page/site. Returns a graph. Some pieces
        inspired by Mesbah et al. 2012.
        https://dl.acm.org/citation.cfm?id=2109208

        Args:
            user: user (instance of UserModel) or user name as string.
            entry_point: An identifier used to specify a specific state. Defaulted to None.

        Returns:
            The built graph.
        """
        if not entry_point:
            entry_point = self.entry_point
        self.pool.add_task(build, entry_point=entry_point, user=user, graph=self.graph,
            delay=self.delay, screenshot_dir=self.screenshot_dir)
        # Complete graph building before continuing with crawl
        self.pool.wait_completion()
        return self.graph

    def crawl_graph(self, user, start_state=None):
        """For the built graph of all possible states and state transitions,
        tag all the edges and states that can be reached by this user."""
        if len(self.graph.states) == 0:
            # Some error probably, no states available.
            # We can't crawl a graph with no states.
            logger.error("Couldn't crawl graph, no states available (probably an error with build_graph).")
            raise Exception("Couldn't crawl graph, no states available (probably an error with build_graph).")

        if user.get_name() in self.crawled_users:
            return  # Already crawled with this user.

        self.crawled_users.add(user.get_name())
        logger.debug('Crawling graph with {}'.format(user.get_name()))
        self.pool.add_task(crawl, user=user, graph=self.graph,
                           build_user=self.config.BUILD_USER.get_name())
        self.pool.wait_completion()

    def reset_graph(self):
        """Reset graph, use after one crawl ends, before another starts."""
        self.graph = Graph()
        self.crawled_users = set()

    def load(self, entry_point):
        """Sets the MultiController entry point.

        Args:
            entry_point: The entry point for the MultiController.
        """
        self.entry_point = entry_point
        return True

    def stop(self):
        """Tell the pool to stop all active threads."""
        self._server.stop()
        self.pool.stop()

    def __del__(self):
        self.stop()
