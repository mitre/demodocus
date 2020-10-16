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

from enum import Flag, auto
import logging
import re


logger = logging.getLogger('crawler.comparator')


class BaseComparator:
    """Base class for Comparators."""
    def match(self, state_data1, state_data2):
        """Determines if two string state_data match.

        Args:
            state_data1: An Access.StateData.get_full_representation()
            state_data2: An Access.StateData.get_full_representation()

        Returns:
            True if they pass and False if they do not pass.
        """
        logger.debug("Running a {} with:\nstate_data1 = [\n\t{}\n\t   ]\nstate_data2 = [\n\t{}\n\t   ]\n".format(\
            self.__class__.__name__, str(state_data1), str(state_data2)))
        return False


class StrictComparator(BaseComparator):
    """A comparator that performs a straight string comparison. It removes
    spaces and semicolons."""
    # This comparator does a straight string comparison.
    # It removes spaces and semicolons.
    # If it passes, we can stop looking.
    def __init__(self):
        self.re_sub = re.compile(r'[;\s]+')

    def match(self, state_data1, state_data2):
        """Determines if two string state_data match.

        Args:
            state_data1: An Access.StateData.get_full_representation()
            state_data2: An Access.StateData.get_full_representation()

        Returns:
            True if they pass and False if they do not pass.
        """
        state_data1 = self.re_sub.sub('', str(state_data1))
        state_data2 = self.re_sub.sub('', str(state_data2))

        match_result = state_data1 == state_data2

        logger.debug("Running a {} with:\nstate_data1 = [\n\t{}\n\t   ]\nstate_data2 = [\n\t{}\n\t   ]\nreturned = {}\n".format(\
            self.__class__.__name__, str(state_data1), str(state_data2), match_result))

        return match_result


class CompareFlag(Flag):
    """Class that holds flags that determines conditions for stop."""
    NONE = 0
    STOP_IF_TRUE = auto()
    STOP_IF_FALSE = auto()
    STOP_ALL = STOP_IF_TRUE | STOP_IF_FALSE


class Comparer:
    """ The Comparer class takes a pipeline of comparators and runs through each in turn. """
    # Use this pipeline if none specified.
    default_pipeline = [
        # Pipeline: pair of (Comparator, CompareFlags)
        # The CompareFlags tell us whether we can stop testing based on the match result.
        (StrictComparator(),          CompareFlag.STOP_IF_TRUE)
    ]

    @classmethod
    def compare(self, state_data1, state_data2, pipeline=None):
        """Runs a pipeline of different comparators against two state_datas.

        Args:
            state_data1: A string representation of a state_data.
            state_data2: A string representation of a state_data.
            pipeline: A list of comparators. Defaulted to None.

        Returns:
            True if the state_datas match any of the comparators in the pipeline.
        """
        if pipeline is None:
            pipeline = self.default_pipeline

        logger.debug("Starting a compare pipeline with:\n\t{}\n"\
            .format(',\n\t'.join([i[0].__class__.__name__ for i in self.default_pipeline])))

        for comparator, flags in pipeline:
            is_last = comparator == pipeline[-1][0]
            try:
                result = comparator.match(state_data1, state_data2)
                # If this is the last comparator, or if we are supposed to skip out early, then stop.
                if result and (is_last or (flags & CompareFlag.STOP_IF_TRUE)):
                    logger.debug("Successfully stopping the comparer with {}\n".format(comparator.__class__.__name__))
                    return True
                elif not result and (is_last or (flags & CompareFlag.STOP_IF_FALSE)):
                    return False
            except Exception as e:
                error_str = "Error running comparator {}: {}".format(comparator.__class__.__name__, str(e))
                logger.error(error_str)
                raise Exception(error_str)
