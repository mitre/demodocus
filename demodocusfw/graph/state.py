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
from pathlib import Path
from threading import Lock
import json

from demodocusfw.comparator import Comparer

logger = logging.getLogger('crawler.graph.state')


class State:
    """A specific configuration of content.
    """
    auto_inc = 0

    def __init__(self, state_data):
        self.lock = Lock()
        with self.lock:
            self.id = State.auto_inc
            State.auto_inc += 1
        self.data = state_data
        self.user_paths = dict()  # Store how each type of user can get here.

    # We're moving stub to the StateData but let's make a property here
    #   so we don't have to change a whole bunch of files.
    @property
    def stub(self):
        return self.data.stub

    def __hash__(self):
        return hash(self.id)

    def __str__(self):
        """Returns a string representation of this state with the ID as well as a description of how to
        reach this state.

        """
        return "State " + str(self.id) + ": " + \
            self.get_user_path_string("OmniUser")

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other):
        """Equality tests. States with the same id are the same.
        Assumes states have been formed correctly, that is, states with the
        same id are the same and states with different ids are different.

        Args:
            other: Another state with which to compare. ID does not matter.

        Returns:
            True if the other state has the same id.
        """
        return self.id == other.id

    def set_user_path(self, user, path):
        """Records the path that a user can take in order to reach this state.

        Args:
            user: user (instance of UserModel) or user name as string
            path: The path to get to this state.
        """
        with self.lock:
            # Mark that the user can reach this state.
            if user.get_name() not in self.user_paths:
                logger.debug('Setting user path: {}, {}'.format(user, path))
                self.user_paths[user.get_name()] = path

    def supports_user(self, user):
        """Determines if this state is reachable by a user.

        Args:
            user: user (instance of UserModel) or user name as string

        Returns:
            True if this state is reachable by a user. False if the state is not reachable by a user."""
        user_name = user if isinstance(user, str) else user.get_name()
        return user_name in self.user_paths

    def get_user_path(self, user):
        """Returns the path to get to this state for a user.

        Args:
            user: user (instance of UserModel) or user name as string

        Returns:
            The path to get to this state for a user. None if this state is not reachable by this user.
        """
        user_name = user if isinstance(user, str) else user.get_name()
        return self.user_paths[user_name] if self.supports_user(user_name) else None

    def get_user_path_string(self, user):
        """
        Gets a string describing the shortest path a user can take to get to
        this state.
        Args:
            user: user (instance of UserModel) or user name as string

        Returns:
            String describing the shortest path a user can take to reach this state.
        """
        user_name = user if isinstance(user, str) else user.get_name()
        ret = ""
        if user_name in self.user_paths:
            ret = " > ".join([str(edge) for edge in self.user_paths[user_name]])
        return ret

    def get_user_names(self):
        """Returns a list of the users that can reach this state"""
        return self.user_paths.keys()

    @classmethod
    def reset_inc(cls, new_id=0):
        """Reset counter to 0 or another starting id."""
        cls.auto_inc = new_id

    def save(self, state_output_dir):
        """Save the state to its own file

        Args:
            state_output_dir: str representing directory to save the state file to
        """
        # Pass it down to the StateData.
        self.data.save(self.id, state_output_dir)


class StateData:
    """ What is a state in this interface?
    What data do we want to store about a state?
    What do we need in order to identify or locate a state?
    What do we need to store in order to distinguish one state from another?
    What is the extension to save a state to a file? What information is saved?
    The StateData gets stored inside graph states as state.data.
    StateData can be overrided by an interface, and again by an app_context"""

    state_ext = "json"

    def __init__(self):
        """Set up any members you want saved in your state data,
        whatever is needed to identify the state in reports, whatever is needed
        to reproduce or recover the state, and whatever
        is needed to distinguish one state from another. """
        self.stub = False
        # Maybe also store javascript variables, cookies, session?

    def __str__(self):
        """Returns a string representation of the StateData object."""
        return self.get_short_representation()

    def __eq__(self, other):
        """This just calls the compare pipeline which is set up in your config file. """
        return Comparer.compare(self.get_full_representation(),
                                other.get_full_representation())
        # TODO: Think about rewriting the Comparators to take a whole StateData.

    def save(self, state_id, state_output_dir):
        # Save the output representation
        state_fname = Path(state_output_dir) / f'state-{state_id}.{self.state_ext}'
        with open(state_fname, 'w', encoding='utf-8') as fp:
            fp.write(self.get_output_representation())

        # Save the output fields to json
        state_fields_fname = Path(state_output_dir) / f'state-fields-{state_id}.json'
        with open(state_fields_fname, 'w', encoding='utf-8') as fp:
            json.dump(self.get_output_fields(), fp, indent=2)

    def get_short_representation(self):
        """Return a short human-readable string for identifying the state in reports or debugging. """
        return "Please define the StateData for your particular Access class."

    def get_full_representation(self):
        """Return a full representation of the state that can be used for distinguishing one state
        from another. """
        return "Please define the StateData for your particular Access class."

    def get_output_representation(self):
        """Returns representation of the state to save to a file."""
        return "Please define the StateData for your particular Access class."

    def get_output_fields(self):
        """Additional fields to output to the gml file.

        Returns:
            output_dict: dictionary of fields to print to the gml file
        """
        return "Please define the StateData for your particular Access class."
