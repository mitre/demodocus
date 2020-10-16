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


class BuildData:
    """Class that captures data about performing an action on an element for the
    build user. This data is later consumed by UserModels that crawl the graph
    to estimate if they could perform that action on that element (at the given
    state), without actually interacting with page.

    The base BuildData class defines the initializer and the only function that
    is meant to be called from other parts of the framework:
    BuildData::get_data(...). This step iterates through all of the implemented
    methods that capture data and lazy loads their value into the
    BuildData::data instance attribute. The base BuildData class here has none
    of these methods implemented. See web/build_data.py::WebBuildData for
    examples.

    Instance attributes:
        methods: list of class methods that are implemented to generate and save
                 build data. Must be created first during the __init__ call,
                 otherwise other instance attributes will be included in this
                 list.
        data: dict of fields saved that describe the page according to the build
              user. This dict is filled with the lazy loading functions that are
              called in get_data().
        is_data_captured: bool denotes whether or not data has been captured.
                          This is initialized to False and only becomes True
                          when get_data() is called. Used to trigger an error if
                          the crawl user receives a BuildData object that has
                          not yet had it's data captured, because get_data() is
                          only called in the build_graph step.
    """

    def __init__(self):
        # Get all methods that are developer defined (and don't start with "_"),
        #  besides build_data(). NOTE: this call has to be first in __init__(),
        #  or else it also pulls instance attributes
        self.methods = [method for method in dir(self)
                        if method[0] != "_" and method != "get_data"]

        self.data = dict()

        self.is_data_captured = False

    def __str__(self):

        return str(self.data)

    def get_data(self, access, action, element):
        """Get all data from the build that is necessary for UserModels to score
        edge traversals.

        Args:
            access: access to the user interface
            action: Action to be performed
            element: Element that is the target of the action

        Returns:
            data: dict of fields pulled from the access during build

        """

        # Hack to call all of the lazy loading methods initialized, and return
        #  self.data, which has keys/values filled when the methods below are
        #  called
        for method in self.methods:
            getattr(self, method)(access, action, element)

        self.is_data_captured = True

        return self.data
