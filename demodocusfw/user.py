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
*UserModel* is the class that provides the framework for representing
a website user.

A UserModel owns multiple *UserAbilities*, which represent the
user's ways of understanding and interacting with a website. A
UserAbility has a set of actions, which specify which Simple Actions
it is able to perform. For instance, a MouseAbility is able to
perform simple mouse actions (see actions/simple.py).

A *User* is an instance of UserModel with a particular configuration
of UserAbilities.

Available users are defined in users/users.py. Some examples are:
- OmniUser: Can perceive and interact with everything, used for building the complete graph
- VizMouseUser: Represents a user without any recognized accessibility needs
- VizKeyUser: Represents a user that cannot use a mouse
"""

from enum import Flag, auto


class ScoreFlag(Flag):
    """
    Constants that represent the scoring functions in the UserModel. The scores
    are:
        PCV: perceive
        NAV: navigate
        ACT: act

    Allows us to call user_model.score(PCV|NAV|ACT, element, simple_action)
    FIXME: See users/base.py for a full description.
    """
    PCV = auto()
    NAV = auto()
    ACT = auto()

    def __contains__(self, item):
        return (self.value & item.value) == item.value


PCV = ScoreFlag.PCV
NAV = ScoreFlag.NAV
ACT = ScoreFlag.ACT


class UserModel:
    """Users perform Tasks to try to alter page content.
    Our user model follows a Perceive-(Think)-Act loop.
    Users have abilities, which affect perceiving and/or acting.
    A low-vision user might have abilities for handling zooming, color contrast, and font spacing

    When a page is loaded, a map of elements to events is stored in the access.

    When crawling, the user simply checks to see if it can perform the specified task for each edge.

    Concepts:
    score_perceive(element): How easy is it for the user to see/hear/etc. the element?
    score_navigate(element): How easy is it for the user to get (scroll, move, tab) to this element?
    score_act(element): How easy is it for the user to trigger the element?

    score_navigate_act(element) = score_navigate * score_act
    score_perceive_navigate_act(element) = score_perceive * score_navigate * score_act
    """

    def __init__(self, name, abilities):
        """UserModel Constructor. Creates an instance of a User.

        Args:
            name: A String representing the name of the User.
            abilities: A list of the abilities the User has access to.

        """
        self._name = name
        self.abilities = set(abilities)
        self.actions = set()
        self.prepared = False
        for ability in self.abilities:
            # Add the abilities' js_events to our collection.
            self.actions |= ability.actions

    def get_name(self):
        """Returns the name of the user."""
        return self._name

    def __str__(self):
        return self.get_name()

    def __hash__(self):
        return hash(str(self))

    def get_actions(self):
        """Returns a list of the actions this user can do."""
        return self.actions

    def _prepare(self, access):
        """Performs any necessary actions on a page to allow for an interaction to occur, should the User
        require it. This should be run before any other functions.
        (Other functions will try to run it automatically.)

        Args:
            access: Access to the user interface for retrieving actionable elements.
        """
        if not self.prepared:
            self.prepared = True
            for ability in self.abilities:
                # Prepare the abilities.
                ability.prepare(access)

    """
    The UserModel contains five main functions, four of which are paired.

    1. score_perceive(element): How well can we perceive this element?
    2. describe(element): Actually perceive the element, gathering a set of descriptive tags.

    3. score_navigate(element): How well can we get to this element?
    4. navigate(element): Actually navigate to the element.

    5. score_act(simple_action, element): How well could we perform the specified action on this element?
    (For more on Simple Actions, see actions/simple.py.)
    """
    def score(self, score_flags, access, element, edge_metrics, action=None):
        """Uses the score flags as a generalized way to access scores. Currently, ACT is the only score
        that requires an action. Can be an iterable of multiple actions.

        NOTE: usually if both element and action are required, they need to be
        specified before edge_metrics is. This is the only case where that order
        is not preserved because action is optional.

        Args:
            score_flags: Some combination of score flags (see above)
            access: A web access (required)
            element: Some element on the page (required)
            edge_metrics: EdgeMetrics object that stores data for a user/edge (required)
            action: an action to perform, if the score involves an action.

        Returns:
            A score between 0 and 1. Returns 0 if action is not in user.actions.
        """
        # If we're checking ACT, first make sure the user can do this action to save time.
        if ACT in score_flags:
            # Remember that action could be an iterable.
            if type(action) in (list, set, tuple):
                if len(set(action) & self.actions) == 0:
                    return 0
            elif action not in self.actions:
                return 0

        pcv = 1
        nav_act = 1
        if PCV in score_flags:
            pcv, _ = self.score_perceive(access, element, edge_metrics)
            if pcv == 0:
                return 0.0
        if (NAV | ACT) in score_flags:
            nav_act, _, nav_score, act_score = self.score_navigate_act(access, element, action, edge_metrics)
            edge_metrics.nav_score = nav_score
            edge_metrics.act_score = act_score
            return pcv*nav_act
        if NAV in score_flags:
            nav_act, _ = self.score_navigate(access, element, edge_metrics)
        if ACT in score_flags:
            nav_act, _ = self.score_act(access, element, action, edge_metrics)
        return pcv*nav_act

    def score_perceive(self, access, element, edge_metrics):
        """Returns a tuple with the score of how well the user can perceive an element and the highest
        scoring ability.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            element: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            (score, ability) where score is a value between 0 and 1 representing how well the user can perceive
            an element, and ability is the highest scoring ability.
        """
        score, ability = max([(ability.score_perceive(access, element, edge_metrics), ability) for ability in self.abilities])
        if score == 0.0:
            ability = None
        edge_metrics.pcv_score = score

        return score, ability

    def describe(self, access, element):
        """
        Based on this user's abilities, attempt to build up a string describing the element.
        Users with different perceptions may end up with different pieces of information.
        This is used if we need to understand an element's purpose, ie, expecting some particular text input.
        Args:
            access: Access to the user interface for retrieving actionable elements.
            element: A particular element on this interface.

        Returns:
            A string describing el.
        """
        self._prepare(access)
        # Accumulate the descriptor sets from each ability, then turn into a string.
        tags = set()
        for c in self.abilities:
            tags |= c.describe(access, element)
        return ' '.join(list(tags)).lower()

    def score_navigate(self, access, element, edge_metrics):
        """Returns a tuple with the score of how well the user can navigate to an element and the highest
        scoring ability.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            element: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            (score, ability) where score is a value between 0 and 1 representing how well the user can
            navigate to an element, and ability is the highest scoring ability.
        """
        self._prepare(access)
        score, ability = max([(ability.score_navigate(access, element, edge_metrics), ability)
                                           for ability in self.abilities])
        edge_metrics.nav_score = score
        return score, ability

    def navigate(self, access, element, edge_metrics, ability=None):
        """Navigates to particular element on an interface.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            element: A particular element on this interface.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.
            ability: Ability used to navigate to a certain element.
        """
        # If no ability specified, find the best one.
        if ability is None:
            _, ability = self.score_navigate(access, element, edge_metrics)
        return ability.navigate(access, element)

    def score_act(self, access, element, action, edge_metrics):
        """Return a tuple with an estimate of how hard it would be to perform action on element and
        the best scoring ability.
        Returns the ACT score from the best scoring ability.
        Assumes we already navigated to the target element.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            element: A particular element on this interface.
            action: A particular action.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            (score, ability) where score is an estimate of how hard it is to perform action on element and
            ability is the best scoring ability of action on element.
        """
        if hasattr(action, "__iter__"):  # Passed in multiple actions. Find the best one.
            actions = action
            act_score, ability, _ = max([
                self.score_act(access, element, action, edge_metrics) + (action,)
                for action in actions
            ])

        elif action in access.get_actions():
            self._prepare(access)
            act_score, ability = max([
                (ability.score_act(access, element, action, edge_metrics), ability)
                for ability in self.abilities
            ])

        else:
            raise ValueError("UserModel::score_act: %s is not an action on interface %s." %
                             (action, access))
        edge_metrics.act_score = act_score

        return act_score, ability

    """
    Functions that combine the ones above for ease of use:
    1. score_navigate_act(simple_action, element): score_navigate * score_act
    2. score_perceive_navigate_act(simple_action, element): score_perceive * score_navigate * score_act
    """

    def score_navigate_act(self, access, element, action, edge_metrics):
        """Returns a tuple with the highest navigating score multiplied by acting score combination
        and the ability that produces this result.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            element: A particular element on this interface.
            action: A particular action.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            (score, ability, nav_score, act_score) where: *score* is the highest
            navigating score multiplied by acting score; *ability* is the
            ability that produces this result; *nav_score* and *act_score* is
            the nav_score and the act_score used to calculate *score*.
        """
        if hasattr(action, "__iter__"):  # Passed in multiple actions. Find the best one.
            actions = action
            results = [
                self.score_navigate_act(access, element, action, edge_metrics)
                for action in actions
            ]
            nav_act_score, ability, nav_score, act_score = max(results)

        elif action in access.get_actions():
            # See if any of our abilities can perform this action on this element.
            actable_abilities = sorted([
                (ability.score_act(access, element, action, edge_metrics), ability)
                for ability in self.abilities
            ], reverse=True)
            if actable_abilities[0][0] == 0.0:
                return 0.0, None  # It is impossible for us to do this action.

            # Try to navigate to the element with each of our actable abilities and choose the best result.
            # If user can act on the element with both keyboard and mouse, but the mouse has a better result, use that.
            results = []
            for act_score, ability in actable_abilities:
                if act_score > 0.0:
                    nav_score = ability.score_navigate(access, element, edge_metrics)
                    results.append((nav_score * act_score, ability, nav_score, act_score))

            nav_act_score, ability, nav_score, act_score = max(results)

        else:
            raise ValueError(
                "UserModel::score_navigate_act: %s is not an action on interface %s." %
                (action, access))

        return nav_act_score, ability, nav_score, act_score

    def score_perceive_navigate_act(self, access, element, action, edge_metrics):
        """ Return a value indicating how hard it would be to trigger this javascript event on this element.
        This is just perceiving score * navigating score * acting score.
        It returns the score as well as the ability that should be used to achieve that score.

        Args:
            access: Access to the user interface for retrieving actionable elements.
            element: A particular element on this interface.
            action: A particular action.
            edge_metrics: EdgeMetrics object that stores data for a user/edge.

        Returns:
            The product of the highest: perceiving score, navigating score, and
            act score.
        """
        self._prepare(access)

        # Try to perceive the element with each of our abilities and find the best result.
        pcv_score, _ = self.score_perceive(access, element, edge_metrics)
        if pcv_score == 0.0:
            return 0.0  # We can't perceive the element.

        nav_act_score, _, nav_score, act_score = self.score_navigate_act(access, element, action, edge_metrics)
        edge_metrics.nav_score = nav_score
        edge_metrics.act_score = act_score
        return pcv_score*nav_act_score
