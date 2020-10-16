# Evaluating a user interface

Demodocus can be extended to evaluate any type of user interface for
accessibility. The `web` interface was the first one developed, meant for
evaluating web-based applications on the desktop or laptop. It is built into the
`demodocusfw` library and will be used for examples throughout this
documentation. Thus, **the following docs are considered optional unless you
want to extend demodocus to a new, non-web interface**.

To extend demodocus to a new user interface, you will be defining:
- An `Access` class for accessing your interface
- A `StateData` class for storing and outputting data pertaining to your
  states
- An `EdgeMetrics` class for storing and outputting data pertaining to your
  edges
- `Action`s supported by your interface
- `User`s of your interface
- A way to tell if performing some action has changed your interface

> **_NOTE:_** Many of these fields can be overwritten by your application. This
may be necessary because there may be different users or data required for
different evaluation contexts for a given interface. For the `web` interface, we
were working in an `accessibility` that specifies User Abilities, `User
Models`, and an `EdgeMetrics` that are specific to applications dealing with
`accessibility` that use a `web` interface.

## The Access Class

Create a class that inherits from `demodocusfw.access.Access`. It provides
generic functions for querying and interacting with your user interface. You can
think of it as a wrapper around your interface. When creating the `Access`
class, you must answer two questions:

- What is a "state" in my interface/context?
- What is an "element" in my interface?

### Interface states

A state is the configuration of content that could change if the user interacts
with it. For instance, in a web application the state could be the document
object model (DOM), which is interpreted by the browser to render a web page.
The DOM determines the layout and appearance of the page. A change in the DOM
usually corresponds with a perceptible change in content. The web state could
also include information like the url of the page and any cookies on the user's
computer. These other fields may vary depending on the crawling context.

1. Define a `StateData` class that inherits from
   `demodocusfw.graph.state.StateData`. Be sure it contains any data you
   need for identifying your state. Override the `get_short_representation`,
   `get_full_representation`, and `get_output_representation` functions. These
   are used for reporting and comparing states (see below for more about state
   comparisons). Also define `get_output_fields`, which is used to store fields
   of the state to the graph gml file.

2. Override the `_create_state_data` function in your `Access` class. This
   should create and return a new `StateData` by observing the current state of
   your user interface. It will be called whenever your interface might have
   changed. Once this is filled in, you can access your interface's current
   state data at any time by calling `Access::get_state_data()`.

3. Override the `set_state_data` function in your `Access` class. This accepts a
   `StateData` object as a parameter and updates the user interface to match it.
   It can also make modifications, injecting hidden code for example.

4. Override the `load` function in your `Access` class. It accepts a resource
   locator, launch command, or other string and uses it to set the user
   interface to an initial state to begin crawling.

5. Override the `reset` and `reset_state` functions. `reset` resets the access
   object so that it doesn't have to be reloaded between crawls of different
   endpoints. `reset_state` is used to clear reset variables that may be
   associated with the current state of the access object.

As Demodocus builds its graph of the user interface, each state in the graph
will contain a `StateData` describing the user interface in that state. You can
access the `StateData` by referencing `State::data`.

> **_NOTE:_** While the `StateData` for an interface may vary depending on the
crawling context, the `Access` class and the functions implemented above
should pertain to any context for a given interface. It's helpful to build a
generic `StateData` for the interface, and then overwrite fields for different
contexts.

### Interface elements

An element is the smallest unit in an interface that the user can interact with.
For `WebAccess`, an element is roughly equivalent to an html DOM element like a
button or checkbox. You need a way to uniquely identify your element so it can
be located on the interface. Web elements for example can be located with an
xpath or css query string.

Define an `Element` class that inherits from
`demodocusfw.access.Access.Element`. Be sure it contains a way to locate your
element in the interface as well as any other element-specific information you
want to store. Override the `get_short_representation` and
`get_full_representation` functions. These are used for reporting and comparing
elements.

There is no standard way to extract elements from your interface for processing.
As you determine your requirements you'll add whatever functions you need to
your `Access` class for getting elements. These functions should all return
objects of type `Element` as you defined above.

> **_NOTE:_** It is very unlikely for an interface `Element` class to vary for
different contexts, so it is programmed as a private class to the `Access`
class.

### Interface edges

When traversing from one state to another, the crawler is able to record
information that describes how it made that traversal, which we store in an
`EdgeMetrics` object. Some fields like `ability_score` (and its sub-scores) are
tracked in the generic implementation of `EdgeMetrics`, while others may only
apply to specific interfaces or contexts. More information about the
`ability_score`, which is the high-level result of the difficulty of making this
state traversal, can be found on the [User Models](user-models.md) page.

> **_NOTE:_** There are other fields that may be worth tracking, depending on
the context, such as the distance the user had to navigate in order to reach the
element they wanted to track. Just like the advice for implementing a
`StateData`, it's helpful to build a generic `EdgeMetrics` for the interface,
and then overwrite fields for different crawling contexts.

## Actions

### Defining Actions

Now that you've defined the structure and representation of your user interface,
you need to think about what user actions it can support. `Element`s on most
graphical desktop interfaces, for example, will respond to mouse clicks and key
presses. In web browsers, mousing over or tabbing to an element can also change
page content. You want to capture any kind of action that could result in a
state change.

After defining your actions, be sure to add them to your `Access` class's
`actions` set by overriding `Access._initialize_actions`.

To define an `Action`, inherit from `demodocusfw.action.Action` and
override the following members:
- `_action_name` A descriptive name for your action, such as "click".
- `__str__` (optional) Specify how your action will be referenced in reports. By
  default this is `_action_name`.
- `get_elements(access)` Query the `Access` and return all elements that might
  respond to this action. Feel free to add new functions to your `Access` class
  to support this operation.
- `_execute_simple(access, element)` Perform the action on the specified
  element. Return None. For instance, for a click `Action` in a web interface,
  this function could inject javascript to click the element.

### Advanced Actions

If you decide you need an action that does more than click an element, you can
instead override `_execute_advanced(access, user, element)`. This function
attempts to interact with the interface as a user would and returns a value
between 0 and 1 indicating how well it succeeded, where 0 means the user would
not or could not complete this action and 1 means the action is trivial for this
user perform.

When do you need an advanced `Action`?
1. If you need to interact with multiple elements.
2. If you need to perform a number of steps or a combination of actions before
   deciding whether content has changed.
3. If the "easiness" of completing the action is dependent on a combination of
   factors.

> **_NOTE:_** It is very unlikely for an interface *Action* class to vary for
different crawling contexts.

#### Example

You want the user to select a menu option, then dismiss any confirmation boxes
that appear. You want the easiness of completing the action to take into account
the number of boxes that had to be dismissed, something like:

total ease = (ease of selecting menu option) * (1/number of confirmation boxes)

You would accomplish this by overriding `_execute_advanced`. In your
implementation you would query the user to find the ease of selecting the menu
option, then tally and dismiss any confirmation boxes.

## Users

Having defined what an element is in your interface and the various actions that
can be performed upon elements, the next step is to define your users. As
described in the [users documentation](user-models.md), `UserModel`s refer to
`UserAbility`s, which refer to `Action`s.

### User Abilities

A `UserAbility` describes a channel or medium available to a user for
interacting with an interface. Common examples you may decide to implement are
the MouseAbility and the KeyboardAbility (for performing actions on elements),
and a Full-Vision or Low-Vision Ability (for perceiving elements).
`UserAbility`s can calculate scores for perceiving, navigating to, and acting on
elements. When defining a `UserAbility`, you may implement any of the following
members.

Abilities focused on perceiving elements will override the following:
- `score_perceive(access, element)` Calculates how well the user can see or
  otherwise be aware of this element, where 0 means the user has no awareness of
  element and 1 means the user is immediately aware of the element and its
  characteristics. This could take into account element size and color contrast.
- `describe(access, element)` Attempts to find out as much about this element as
  possible by examining the interface. Returns a set of arbitrary descriptive
  strings, which can be used when doing calculations in
  `Action::_execute_advanced` (see above). This could take into account any
  labels associated with the element, as well as the element's type and styling.

Abilities focused on activating elements will override the following:
- `actions` A set of all actions this `UserAbility` can do. For instance, a
  MouseAbility can perform clicking and mouseover actions. These should match
  `Action`s in your `Access` class's `actions` set (see above).
- `score_navigate(access, element)` Calculates how well the user can maneuver
  into place to interact with this element, where 0 means the user cannot
  interact with the element and 1 means the user doesn't need to do anything
  before interacting with the element. Can take into account scrolling, moving
  the mouse, tabbing keyboard focus, etc. If your interface is not graphical,
  this score may just return 1. You should decide what navigating means in your
  interface.

> **_NOTE:_** `UserAbility`s should be customized for different `app_context`s
in order to track intermediate data through the `EdgeMetrics` object. See the
code in `demodocusfw/web/accessibility/ability.py` for the `web` interface /
`accessibility` context.

### Defining users

A user is defined by instantiating the `UserModel` class. It expects a name and
a set of `UserAbility`s.

```python
vision_ability = VisionAbility()
keyboard_ability = KeyboardAbility()
mouse_ability = MouseAbility()
user1 = UserModel('User1', [vision_ability, keyboard_ability, mouse_ability])
```

> **_NOTE:_** Similar to how `UserAbility`s should be customized for different
`app_context`s, `UserModel`s should be as well.

### Advanced action calculations with users

When filling in `_execute_advanced(access, user, element)`, you can of course
call any functions you've defined in your `Access` class and `Element` class to
perform your calculations, as well as the following functions on the user (see
below for more details):
- `user.score(PCV, access, element, action)` How well can the user perceive this
  element, 0-1, where 0 is not at all and 1 means the user is fully aware of the
  element and its characteristics.
- `user.score(NAV, access, element, action)` How well can the user maneuver into
  place to interact with this element, 0-1, where 0 is not at all and 1 means
  the user is already positioned to interact with the element.
- `user.score(ACT, access, element, action)` How well can the user do this
  action on this element, 0-1, where 0 is not at all and 1 means performing this
  action is trivial for this user. Returns 0 if action is not in the user's
  defined set of actions.
- `user.score(PCV|NAV|ACT, access, element, action)` Returns a score that is the
  combination of those above. Any combination of PCV, NAV, ACT is allowed.
- `user.describe(access, element)` Returns a string that is a space-delimited
  set of user-defined keywords describing this element. Different users will
  return different collections of keywords depending on their abilities.

## State comparisons

When deciding how to compare states, you can ask *Would the user care about this
change?* Let's say you move the mouse over a button and it changes from blue to
yellow. This change didn't result in any new information, so it probably
shouldn't be considered a distinct state. In contrast, if you mouse over a
button and text appears, this new informational content is probably important
for the user. That is, we want to know how easy it would be for the user to
access this content. Therefore the mouse-over text should be treated as a
separate state, and we need a comparison function that will be able to
distinguish it from the previous state.

One comparison function (called a `Comparator`) has been provided in
`demodocusfw.comparator.StrictComparator`. `StrictComparator` does a
string-equals operation on the full representations of two `StateData`s, after
stripping whitespace and semicolons. Notice that it inherits from
`BaseComparator` and has a `match` function that accepts the two `StateData`
full representations and returns True or False. You can use this as an example
for making whatever Comparators are needed for your interface.

These will be put together in the configuration file (see below). You will
create a compare pipeline, which defines a sequence for your comparators. For
each comparator you specify one of the following:
- `CompareFlag.STOP_IF_TRUE` If this comparator returns True, these two states
  match. Exit the pipeline and return True.
- `CompareFlag.STOP_IF_FALSE` If this comparator returns False, these two states
  are different. Exit the pipeline and return False.

If the pipeline finishes without having exited early, it returns the result of
the last comparator in the pipeline.

> **_NOTE:_** `Comparator`s can be customized for different contexts. To do
> this, simply code the customized `Comparator` code as needed,
and import it accordingly in the config.

## Configuration

The last step is to [create your own configuration file](configuration.md).
Specify the new classes you just created, as well as any new configuration
parameters expected by your `Access` class. Below is an example from a web
config.

```python
from demodocusfw.config.mode_default import *
from demodocusfw.web.user import OmniUser
from demodocusfw.web.web_access import ChromeWebAccess

#
# Access specification - Fill in these after you have defined your Access class and Users.
#

# Specify your Access class which overrides interfaces/access.py::Access
ACCESS_CLASS = ChromeWebAccess
# Which UserModel should be the one building the graph?
BUILD_USER = WebOmniUser

#
# Web-specific parameters
#

# Make webdriver browser instance invisible to crawler users?
# Default True (invisible). Note that when HEADLESS == False, a browser
# window will open for every active thread.
HEADLESS = True

SCREENSHOTS = False
```

On top of that, we have a config for context-specific classes and fields.
Below is an example from an accessibility config:

```python
from .mode_web import *

from demodocusfw.comparator import StrictComparator, CompareFlag
from demodocusfw.web.accessibility.edge import AccessibilityEdgeMetrics
from demodocusfw.web.accessibility.user import VizKeyUser, VizMouseKeyUser, \
    SuperVizMouseKeyUser, LowVizMouseKeyUser
from demodocusfw.web.comparator import DOMStructureComparator, \
    TextComparator as WebTextComparator

#
# Accessibility AppContext-specific parameters
#
# Which UserModels should attempt to crawl the graph built by OmniUser?
CRAWL_USERS = [VizKeyUser, VizMouseKeyUser,
               SuperVizMouseKeyUser, LowVizMouseKeyUser]

# Comparator pipelines
COMPARE_PIPELINE = [
    # Pipeline: pair of (Comparator, CompareFlags)
    # The CompareFlags tell us whether we can stop testing based on the match result.
    (StrictComparator(),          CompareFlag.STOP_IF_TRUE),
    (DOMStructureComparator(),    CompareFlag.STOP_IF_FALSE),
    (WebTextComparator(),         CompareFlag.STOP_IF_FALSE)
]

# Class to store data for a state traversal. Defaulted to the interface, but
# can be overwritten for a specific app_context
EDGE_METRICS = AccessibilityEdgeMetrics
```

[Run Demodocus](running-crawls.md) using this new mode and pass a launch_string
handled by your `Access::load` function. It will launch and crawl the user
interface as you've defined it, evaluating its accessibility for each of the
users specified.

```bash
python crawler.py <url_or_other_launch_string> --mode <my_mode>
```
