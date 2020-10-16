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
from threading import Lock

logger = logging.getLogger('crawler.edge')


class Edge:
    """A directed edge in a graph. The edge represents moving from an initial state to another state
    by performing an action on a specific element."""
    def __init__(self, s1, s2, element, action):
        self.lock = Lock()
        self.state1 = s1
        self.state2 = s2
        self.element = element  # The element that is acted upon in this transition
        self.action = action  # The action that caused this transition
        self.user_metrics = {}  # Dictionary of user name to EdgeMetrics

    def __str__(self):
        """String representation of an Edge.

        Returns:
            A string indicating an edge from one state to another state via an action on an element.

        """
        return 'from {} to {} via {} on {}'.format(self.state1.id,
            self.state2.id, self.action, self.element)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        # TODO: must this check users and/or users, does it matter?
        if self.state1 == other.state1 \
                and self.state2 == other.state2 \
                and self.element == other.element \
                and self.action == other.action:
            return True
        return False

    def __hash__(self):
        # Note: sets aren't hashable, so convert to tuple for hashing
        return hash((self.state1, self.state2, self.element, self.action))

    def add_data_for_user(self, user, edge_metrics):
        """Add data for a user that can traverse this edge.

        Args:
            user: user (instance of UserModel) or user name as string
            edge_metrics: EdgeMetrics object that stores data for a user/edge.
        """
        with self.lock:
            # add the user and the score if it doesn't already exist
            if user.get_name() not in self.user_metrics:
                self.user_metrics[user.get_name()] = edge_metrics
            # update the score only if it's GT the existing score
            elif edge_metrics.ability_score > self.user_metrics[user.get_name()].ability_score:
                logger.debug(f'Overwriting edge_metrics for edge [{str(self)}] and'
                             f' user [{str(user)}]')
                self.user_metrics[user.get_name()] = edge_metrics

    def supports_user(self, user):
        """Determines whether this edge supports a user

        Args:
            user: user (instance of UserModel) or user name as string

        Returns:
            True if the user is supported on this edge. False if the user is not supported on this edge.
        """
        user_name = user if isinstance(user, str) else user.get_name()
        return user_name in self.user_metrics

    def get_user_data(self, user):
        """Returns the score of a user on this edge.

        Args:
            user: user (instance of UserModel) or user name as string

        Returns:
            The score of the user on this edge. 0 if the user is not supported on this edge.
        """
        user_name = user if isinstance(user, str) else user.get_name()
        if user_name in self.user_metrics.keys():
            edge_output_fields = self.user_metrics[user_name].get_output_fields()
            user_data = {user_name: self.user_metrics[user_name].ability_score}
            for k, v in edge_output_fields.items():
                user_data[f"{user_name}_{k}"] = v
            return user_data
        else:
            # user was not supported by this edge. Return a score of 0 on this
            #  edge for the user for easier downstream analysis.
            return {user_name: 0}

    def get_user_names(self):
        """Returns a list of the users supported on this edge"""
        return self.user_metrics.keys()


class EdgeMetrics:
    """Stores data about traversing from one state to another for a particular
    user.

    By default, it must store an ability_score, the ability sub-scores (pcv,
    nav, act scores), and the time it takes to perform an action to crawl
    successfully. Additional fields can also be tracked. Any fields that should
    be outputted to the gml graph file should be specified in
    get_output_fields().

    The build_data field tracks the data generated by the build and is the only
    exception to how data is outputted from EdgeMetrics, as this field will only
    be outputted for the build_user and does not need a helper function to
    output its data like get_output_fields().
    """

    def __init__(self):
        # Fields with specialized getter/setter methods (implemented below).
        self._ability_score = None
        self._pcv_score = None
        self._nav_score = None
        self._act_score = None
        self._act_time = None

        # Setting default values for class fields that DO NOT require
        # specialized getter/setter methods.
        self.error = None  # Set this to any error during calculation.
        self.build_data = None # BuildData object with data captured in build_graph

    # --
    # Getter and setter methods for metrics.
    #
    # Ensure that you only overwrite a metric if the new value is "better" than
    #  the existing one.
    #

    @property
    def ability_score(self):
        return self._ability_score

    @ability_score.setter
    def ability_score(self, ability_score):
        if self._ability_score is None or ability_score > self._ability_score:
            self._ability_score = ability_score

    @property
    def pcv_score(self):
        return self._pcv_score

    @pcv_score.setter
    def pcv_score(self, pcv_score):
        if self._pcv_score is None or pcv_score > self._pcv_score:
            self._pcv_score = pcv_score

    @property
    def nav_score(self):
        return self._nav_score

    @nav_score.setter
    def nav_score(self, nav_score):
        if self._nav_score is None or nav_score > self._nav_score:
            self._nav_score = nav_score

    @property
    def act_score(self):
        return self._act_score

    @act_score.setter
    def act_score(self, act_score):
        if self._act_score is None or act_score > self._act_score:
            self._act_score = act_score

    @property
    def act_time(self):
        return self._act_time

    @act_time.setter
    def act_time(self, act_time):
        if self._act_time is None or act_time < self._act_time:
            self._act_time = act_time

    # --
    # Other functions
    #

    def get_output_fields(self):
        """Additional fields to output to the gml file for a given user model.

        The fields in build_data are only outputted for the build_user and do
        not need to be specified here. See Graph::to_gml method.

        Returns:
            output_dict: dictionary of fields to print to the gml file
        """
        return {"score": self.ability_score,
                "pcv_score": self.pcv_score,
                "nav_score": self.nav_score,
                "act_score": self.act_score,
                "act_time": self.act_time}
