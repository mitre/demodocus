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
import os
import re
import tempfile
import time

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    JavascriptException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    UnexpectedAlertPresentException,
    NoAlertPresentException,
    WebDriverException
)

from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.color import Color
from selenium.webdriver.common.keys import Keys

from .dom_manipulations import (
    collapse_newlines,
    insert_after,
    insert_before,
    js_calculate_reachable,
    js_freeze_element_data,
    js_end,
    js_get_xpath,
    js_start,
    js_get_computed_outline,
    js_focus_first_tabbable,
    manage_event_listeners,
    strip_demodocus_ignore,
    RE_HTML,
    RE_HTML_CLOSE,
    REACHABLE_ATT_NAME
)

from .template import HtmlTemplate
from demodocusfw.access import Access
from demodocusfw.utils import get_output_path
from demodocusfw.web.action import (
    FormFillAction,
    keyboard_actions,
    mouse_actions
)
from demodocusfw.web.controller import ControllerReduced, \
    MultiControllerReduced
from demodocusfw.web.server import ThreadedHTTPServer
from demodocusfw.web import utils as wutils


logger = logging.getLogger('crawler.webaccess')


class WebAccess(Access):
    """This interface talks to selenium and whatever else to access the web.
    Any class that interacts with the browser can inherit from this interface.
    It should then override all of these methods."""

    # --
    # Defining what the elements are in this interface
    #
    class Element(Access.Element):
        """ In a web interface an element is basically a Selenium element.
        We'll also store the xpath for locating it on the page.
        Must specify either xpath or selenium_element or lxml_element
        """
        def __init__(self):
            # These get filled in by Access::_get_element
            self.xpath = None
            self._selenium_element = None
            self._lxml_element = None

        def get_short_representation(self):
            """Returns a short string representation of the state."""
            return self.xpath

        def get_full_representation(self):
            """Returns a full string represenation of the state."""
            return self.xpath
        
        def __eq__(self, other):
            # Check to see if the element is in the same location in the dom.
            # In what cases is this not good enough? Consider cnn.com -- sometimes
            #   divs are out of order or inserted randomly.
            return self.xpath == other.xpath
            
        def __hash__(self):
            return hash(str(self))

    @classmethod
    def make_controller(cls, config):
        """Given the config returns a controller to use. This can vary by interface."""
        if config.REDUCED_CRAWL:
            if config.NUM_THREADS > 1 or config.MULTI:
                return MultiControllerReduced(cls, config)
            else:
                return ControllerReduced(cls, config)
        else:
            return super().make_controller(config)

    # There will be a server at the class level for serving up content from the output folder.
    _server = None

    # --
    # Constructor and destructor
    #
    def __init__(self, config):
        """
        Args:
            config: A loaded config object. The access will use this to configure itself.
        """
        super(WebAccess, self).__init__(config)
        self._events = None
        self._driver = None
        self._config = config
        self._entry_state = None
        self._current_state = None
        self._max_tabs = 200

    def __del__(self):
        """ Ensures that the Web Access cleans up its dependencies after use. """
        self.shutdown()

    def _create_driver(self, config):
        """ Creates a web driver. Override this. """
        raise NotImplementedError("Must override WebAccess::_create_driver.")

    def shutdown(self):
        if self._driver is not None:
            self._driver.quit()
            self._driver = None

    @classmethod
    def _initialize_actions(cls):
        # cls._actions = {MouseOver.get(), MouseOut.get()}
        cls._actions = mouse_actions | keyboard_actions
        cls._actions.add(FormFillAction.get())

    # --
    # Overridden functions from Access
    #
    def load(self, url):
        """Navigates to the entry point, loads it up without running JavaScript and saves it.
        This "bare bones" version of the entry page will be used when forward-tracking to states.
        Then the function injects the source back into the browser (with JavaScript) to begin crawling.

        Args:
            url: Page url

        Returns:
            True if the page successfully loaded, else false.
        """
        # Download the raw dom to our local build folder so we can load it quickly.
        self._save_raw_dom_to_local(url)
        # Randomized content check:
        # Load it multiple times and see if any content has changed.
        # This is not foolproof. Sometimes we load a page three times and won't find
        #   all the randomized content, or any at all.
        if self._driver is None:
            self._create_driver(self._config)
        load_count = 0
        template = HtmlTemplate()
        longest_load_time = 0
        while load_count < self._config.PAGE_CHANGE_NUM_LOADS:
            load_count += 1
            logger.info(f"Page load #{load_count}")
            # Load it back into the browser so the javascript will run.
            if not self._load_raw_dom_from_local():
                return False  # We can't proceed if we can't load the page.
            self.reset_state()
            load_time, template2 = self.wait_for_stable_template(seconds_threshold=self._config.PAGE_CHANGE_THRESHOLD,
                                                                 seconds_timeout=self._config.PAGE_CHANGE_TIMEOUT)
            longest_load_time = max(longest_load_time, load_time)
            if template2.is_stable():
                logger.info(f"{url} took {load_time} seconds to stabilize.")
            else:
                logger.warning(f"{url} loaded in {load_time} seconds except for unstable xpaths: {template2.get_unstable_xpaths()}")
            template.add_template(template2)
        for el_xpath in sorted(template.get_unstable_xpaths()):
            # When we do comparisons, we should remove or ignore these elements.
            # Maybe do: If there is a lot of changing content under a particular ancestor, ignore the whole ancestor?
            logger.info(f"Found unstable content {el_xpath}")

        self.wait_for_animation()  # Have to do this to freeze the styles and positions.
        self._current_state_data = self._create_state_data()
        # Explore all reachable elements.
        self._current_state_data.elements_to_explore = self.query_xpath('html/body//*[@demod_reachable="true"]')
        self._current_state_data.load_time = longest_load_time
        self._current_state_data.template = template
        return True

    def set_state(self, state):
                
        # Now follow the edges to get to the desired state.
        path = state.get_user_path(self._build_user)

        # close all tabs besides the first one
        while self._driver and len(self._driver.window_handles) > 1:
            self._driver.close()
            self._driver.switch_to.window(self._driver.window_handles[-1])
            
        if path is None or len(path) == 0:
            self._entry_state = state
        else:
            if self._entry_state is None:
                self._entry_state = path[0].state1

        if path is None or len(path) == 0:
            # If path is None, assume state is state 0.
            if not self._load_raw_dom_from_local():
                return False
            _, t2 = self.wait_for_stable_template(seconds_interval=.2, seconds_timeout=.4)
            self._entry_state.data.template.add_template(t2)
            self._current_state_data = state.data
        else:
            # Get the raw start data from state 0 (should be the first state in the path).
            # Write the start dom to the page.
            if not self._load_raw_dom_from_local():
                return False
            _, t2 = self.wait_for_stable_template(seconds_interval=.2, seconds_timeout=.4)
            self._entry_state.data.template.add_template(t2)
            # Perform actions to get from state 0 to state.
            # TODO this will not put a build_data object onto the state that we
            #  are eventually setting. If the OmniUser/build_user needs
            #  build_data to build the graph, this will need to be placed
            #  somewhere, probably on self._current_state_data
            for edge in path:
                self.perform_action_on_element(self._build_user, edge.action, edge.element, revisit=True)

        self._current_state = state
        self._current_state_data = state.data
        self.reset_state()
        return True

    def _create_state_data(self):
        """Retrieves the current state of the interface.
        Gets the entire dom. From https://stackoverflow.com/a/25592922, but see
        https://stackoverflow.com/a/25646401 below it on that same page for
        caveats.

        Returns:
            A StateData object representing the current state
        """
        sd = self._state_data_cls(self._driver.current_url, self._get_dom())
        if self._current_state_data is not None:
            # Just set the stub status right here when we create the new state data.
            sd.stub = not self.is_state_valid()
            if not sd.stub:
                if self._current_state_data.template is not None:
                    # If this state is the same url path as the first, carry over the template.
                    #   get_updated will attempt to update the old state's template with any
                    #   new stable content from the new state. It will assume that any unstable
                    #   content from the old state carries over.
                    sd.template = self._current_state_data.template.get_updated_template(sd.dom)
        return sd

    # We want to replace any relative or absolute links with the absolute paths.
    # Doesn't handle rel links that get added by javascript, but the history script, which changes the url,
    #   should take care of that.
    # Different examples of things we need to capture for a website like http://domain/path:
    #   href="css/main.css" -> href="http://domain/path/css/main.css"
    #   src="/wp/wp-includes/js/wp-embed.min.js?ver=5.2.7" -> src="http://domain/wp/wp-includes/js/wp-embed.min.js?ver=5.2.7"
    #   href="/.a/bundles/header.aefd20da933a91d1c224.bundle.js" -> href="http://domain/.a/bundles/header.aefd20da933a91d1c224.bundle.js"
    # Don't change:
    #   href="http://www.bob.gov/css"
    #   href="https://edition.cnn.com"
    #   href="//data.api.cnn.io"
    RE_REL_LINK = re.compile(r"""(src|href)=("|')(?!http|//|/)(.*?)\2""", flags=re.DOTALL | re.UNICODE)
    RE_ABS_LINK = re.compile(r"""(src|href)=("|')(?!http|//)/(.*?)\2""", flags=re.DOTALL | re.UNICODE)

    # Remove any attempts to set document.domain (ARRG CNN)
    RE_BROKEN_OPS = re.compile(r"""window\.document\.domain\s?=\s?("|').*?\1;""")

    def _save_raw_dom_to_local(self, url):
        """Grabs the raw page source from the server, without running any script on it.
        Then injects additional Javascript to do the following post-processing:
        - Monitor any event-handler registrations and add them to a list.
        - Inject some utility functions to allow getting xpaths etc.
        - See ./dom_manipulations for more details.
        Saves the result to disk so it can be quickly loaded later.
        """
        # When we first load the page, don't run any javascript.
        response = requests.get(url, verify=False)
        if response.status_code != 200:
            return False
        response.encoding = response.apparent_encoding

        # Many pages have broken code that is fixed by the browsers. We use
        # BeautifulSoup to fix the code for us
        soup = BeautifulSoup(response.text, "html5lib")

        raw_dom = str(soup)
        # Overwrite the url to be the state's url.
        # This will help with relative links.
        # The --disable-web-security Chrome flag needs to be set to allow this.
        history_script = "history.replaceState(null, '', '{URL}');".replace('{URL}', url)
        # This creates a javascript warning on external pages, which we should be able to
        #   get rid of by running in the page context.
        # Change all relative sources to be absolute.

        # Get absolute url as it may have been redirected
        # e.g., https://wisconsindot.gov/Pages/home.aspx -> https://wisconsindot.gov
        # Resources will use src|href="/path/to" which needs absolute path
        split_url = url.split('/') # Gives ['http:', '', 'domain.com', ...]
        abs_url = f"{split_url[0]}//{split_url[2]}"

        # Cut off any trailing slash.
        if url[-1] == "/":
            url = url[:-1]

        modified_dom = raw_dom
        modified_dom = self.RE_BROKEN_OPS.sub("", modified_dom)
        modified_dom = self.RE_ABS_LINK.sub(rf"""\1=\2{abs_url}/\3\2""", modified_dom)
        modified_dom = self.RE_REL_LINK.sub(rf"""\1=\2{url}/\3\2""", modified_dom)
        modified_dom = manage_event_listeners(modified_dom)
        js_demodocus_flag_start = js_start + 'demodocus_done=false;' + history_script + js_end
        modified_dom = insert_after(modified_dom, RE_HTML, js_demodocus_flag_start)
        modified_dom = insert_before(modified_dom, RE_HTML_CLOSE, js_start + 'demodocus_done=true;' + js_end)
        output_path = get_output_path(self._config)
        # Save to disk.
        # The pure raw dom isn't used anywhere; it's just for debugging.
        with open(output_path / "raw.html", 'w', encoding='utf-8') as fp:
            fp.write(raw_dom)
        # The modified raw dom is loaded whenever we go to a new state.
        with open(output_path / "raw_modified.html", 'w', encoding='utf-8') as fp:
            fp.write(modified_dom)

        return True

    def _load_raw_dom_from_local(self):
        """Use this during graph building, when returning to a visited state.
        Also use it when crawling the graph.
        Loads the raw dom of the initial state from disk.
        """
        if self._driver is None:
            self._create_driver(self._config)
        else:
            self.reset_state()

        raw_fname = "raw_modified.html"
        # Sometimes I'm getting TimeoutException. Just keep trying.
        url = f'http://{self._config.server_ip}:{self._config.server_port}/{raw_fname}'
        my_exception = None
        for i in range(1, 5):
            try:
                self._driver.get(url)
                # Each time we load it, augment the template.
                # What are the multithreaded considerations?
                return True
            except TimeoutException as e:
                logger.warning(f"Timed out loading raw page from {url}.")
                my_exception = e
                continue
        logger.error(f"Failed to load page from {url}: {my_exception}")
        return False

    def wait_for_stable_dom(self, seconds_interval=2.0, seconds_timeout=20.0, seconds_threshold=6.0):
        """Waits for the dom to stop changing.

        Args:
            seconds_interval: Interval to check page content
            seconds_timeout: Time to stop checking page content
            seconds_threshold: Require the page to be stable for this amount of time.
        Returns:
            Number of seconds it took for the page to stabilize.
        """
        new_dom = self._get_dom()
        # Now set a time to see if the content keeps changing.
        seconds_spent = 0
        stable_timestamp = -1
        while seconds_spent < seconds_timeout:
            prev_dom = new_dom
            time.sleep(seconds_interval)
            seconds_spent += seconds_interval
            new_dom = self._get_dom()
            # Don't allow an empty body, which indicates nothing has loaded yet.
            # Example: cnn.com
            if new_dom == "<body></body>":
                continue
            # Do a straight string compare to see if anything is changing in the dom.
            if new_dom == prev_dom:
                if stable_timestamp == -1:
                    stable_timestamp = seconds_spent - seconds_interval  # Stable as of previous check.
                if stable_timestamp >= 0 and seconds_spent - stable_timestamp >= seconds_threshold:
                    self._calculate_reachable()
                    if self.try_dismiss_popup():
                        self._calculate_reachable()  # We dismissed the popup so calculate reachable again.
                    return stable_timestamp
            else:
                stable_timestamp = -1  # Page is no longer stable.
        # Timed out.
        if stable_timestamp == -1:
            # We didn't stabilize in time.
            self._calculate_reachable()
            if self.try_dismiss_popup():
                self._calculate_reachable()  # We dismissed the popup so calculate reachable again.
            return stable_timestamp
        else:
            self._calculate_reachable()
            if self.try_dismiss_popup():
                self._calculate_reachable()  # We dismissed the popup so calculate reachable again.
            return stable_timestamp

    def wait_for_stable_template(self, seconds_interval=2, seconds_timeout=20, seconds_threshold=6):
        """Waits for the page dom to stop changing and returns a template representing the page.

        Args:
            seconds_interval: Interval to check page content
            seconds_timeout: Time to stop checking page content
            seconds_threshold: Require the page to be stable for this amount of time.
        Returns:
            Number of seconds it took for the page to stabilize,
            and any elements that were still changing when the function timed out.
        """
        # The threshold cannot be greater than the timeout!
        if seconds_threshold > seconds_timeout:
            seconds_threshold = seconds_timeout
        seconds_spent = 0
        stable_timestamp = -1
        prev_dom = None
        # Track all templates generated over the course of waiting. Contains (time, template) pairs.
        templates_by_timestamp = list()
        while True:
            # Extract the dom from the browser.
            self._calculate_reachable()  # (Have to do this before detecting popups.)
            if self.try_dismiss_popup():
                self._calculate_reachable()  # We dismissed the popup so calculate reachable again.
            new_dom = self._get_dom()  # Get the new dom with reachable information.

            if prev_dom is not None:
                # Straight string compare to see if anything is changing in the dom.
                if new_dom == prev_dom:
                    if stable_timestamp == -1:
                        # Stable as of previous check.
                        stable_timestamp = seconds_spent - seconds_interval
                    if stable_timestamp >= 0 and seconds_spent - stable_timestamp >= seconds_threshold:
                        # The dom has been stable longer than threshold so we can return.
                        return stable_timestamp, HtmlTemplate(new_dom)
                else:
                    # Dom is no longer stable.
                    # Make a template the reflects the differences between the two timestamps.
                    template = HtmlTemplate(prev_dom, new_dom)
                    templates_by_timestamp.append((seconds_spent, template))
                    stable_timestamp = -1

            prev_dom = new_dom
            time.sleep(seconds_interval)
            seconds_spent += seconds_interval
            if seconds_spent > seconds_timeout:
                break

        # We didn't stabilize in time. Get a template reflecting the changing elements.
        template = HtmlTemplate(prev_dom, new_dom)
        unstable_xpaths = template.get_unstable_xpaths()
        # Go backward through each previous template comparing the unstable elements.
        # As long as the unstable element set matches the current one, keep combining the templates.
        # If the unstable element set is different, queue up the template in case this was a cycle.
        # In the case of a cycle, different element sets change and stop changing over time in a repeating pattern.
        # To detect a cycle we determine if the currently changing element set has changed
        # (and then stopped changing) before. The time between now and the previous change is the cycle's period.
        # When we detect a cycle we combine all templates that are part of the cycle to get the full
        # list of changing elements in the cycle.
        # We do not stop at one period but keep moving all the way back through all the templates we gathered
        # in case we captured multiple periods.
        stable_index = len(templates_by_timestamp)-1
        queued_templates = list()
        for i in range(len(templates_by_timestamp)-1, 0, -1):
            seconds, t2 = templates_by_timestamp[i]
            xpaths = t2.get_unstable_xpaths()
            if xpaths == unstable_xpaths:
                # The same set of elements was changing, so add this template.
                template.add_template(t2)
                # If there are any queued templates, this is a cycle.
                # Add the queued templates.
                for t3 in queued_templates:
                    template.add_template(t3)
                # Mark the index before this set of element(s) started changing.
                stable_index = i-1
            else:
                # Different element(s) were changing. Queue up this template in case we have a cycle.
                queued_templates.append(templates_by_timestamp[i][1])
        stable_index = max(stable_index, 0)
        stable_timestamp = templates_by_timestamp[stable_index][0]
        return stable_timestamp, template

    def wait_for_animation(self):
        """Called after changing the page. Waits for any animation to play.
        Similar to wait_for_stable_dom but pays attention to element styling and positioning.
        """
        # Freeze current element data so we can see if it changes.
        self._freeze_element_data()
        dom = self._get_dom()
        prev_dom = dom
        # Now set a time to see if the content keeps changing.
        # Don't wait for more than 5 seconds for an animation to complete.
        seconds_timeout = 5
        seconds_spent = 0
        seconds_interval = .2
        while seconds_spent < seconds_timeout:
            time.sleep(seconds_interval)
            self._freeze_element_data()
            new_dom = self._get_dom()
            # Do a straight string compare to see if anything is changing in the dom.
            if new_dom == prev_dom:
                break
            prev_dom = new_dom
            seconds_spent += seconds_interval

    def capture_screenshot(self, output_path):
        """Get a screenshot from the access of the current state

        Args:
            state_id: int id of the state to get a screenshot from
        """
        self._driver.get_screenshot_as_file(str(output_path))

    def get_elements_to_explore(self):
        return self._current_state.data.elements_to_explore

    def try_dismiss_popup(self):
        """Tries to dismiss any alert or popup on the screen.
        Call this only after _calculate_reachable has been called.

        Returns:
            True if a popup was found.
        """
        try:
            self._driver.switch_to.alert.accept
            logger.warning("Javascript alert found, dismissing.")
            return True
        except NoAlertPresentException:
            # There is no alert box.
            try:
                popup_keywords = {"Modal", "Popup", "Overlay"}
                # See if there is some sort of close button we can click.
                popup_xpath = [f"""contains(., "{keyword}") or contains(., "{keyword.lower()}")""" for keyword in popup_keywords]
                popup_xpath = """//*[@*[""" + " or ".join(popup_xpath) + """]]"""
                # for keyword in popup_keywords:
                # modal_xpath += f"""//*[@*[contains(., "{keyword}") or contains(., "{keyword.lower()}")""" + \
                #                 """ or contains(., "popup") or contains(., "Popup")""" + \
                #                 """ or contains(., "overlay") or contains(., "Overlay")]]"""
                # The close button can either be a button or something with role=button.
                close_button_xpaths = {
                    """//*[@role="button"][@demod_reachable="true"][@*[contains(., "close") or contains(., "Close")]]""",
                    """//button[@demod_reachable="true"][@*[contains(., "close") or contains(., "Close")]]"""
                }
                close_button_xpaths = {popup_xpath + close_button_xpath for close_button_xpath in close_button_xpaths}
                close_button_xpath = "|".join(close_button_xpaths)
                close_button = self._driver.find_element_by_xpath(close_button_xpath)
                logger.warning("Popup found, dismissing.")
                close_button.click()
                return True
            except NoSuchElementException:
                return False

    def perform_action_on_element(self, user, action, element, revisit=False):
        """Attempts to have user perform action on element.
        This is the same implementation as found in the parent Access class, but
        handles the possibility of a new state opening as a result of the
        action.execute call.

        Args:
            user: UserModel to perform the action
            action: Action to be performed
            element: Element that is the target of the action.
            revisit: bool to not get build_data if True (default is False). Only
                     True when we call web_access.set_state(), since we don't
                     care about scores/data in that use.

        Returns:
            edge_metrics: contains all of the data to assess the results of
                          performing the action on the element.
        """

        # Track the set of tabs open prior to calling action.execute
        prior_tabs = set(self._driver.window_handles)
        # Track dom prior to calling action.execute
        prev_dom = self._get_dom()
        prev_url = self._driver.current_url

        edge_metrics = self._create_edge_metrics()

        # Get build_data (only do when we are first visiting the state)
        if not revisit:
            build_data = self._build_data_cls()
            _ = build_data.get_data(self, action, element)
            edge_metrics.build_data = build_data

        # When we execute a web action, we try to run a Selenium action and then handle any Selenium exceptions.
        # For an action to be successful, we need to be able to both activate the element and retrieve the resulting
        # dom. 
        retries = 3
        while retries > 0:
            retries -= 1

            # Make sure the element still exists.
            sel_el = self.get_selenium_element(element)
            if sel_el is None:
                message = f"Could not perform {action} on {element}: Element no longer exists."
                logger.error(message)
                edge_metrics.error = NoSuchElementException(message)
                edge_metrics.ability_score = 0.0
                return edge_metrics
                
            # Make sure the element is reachable.
            if sel_el.get_attribute('demod_reachable') == "false":
                # If it's not reachable, maybe we need to dismiss a popup.
                if not self.try_dismiss_popup():
                    message = f"Could not perform {action} on {element}: " \
                              f"Element is not reachable."
                    logger.error(message)
                    edge_metrics.error = NoSuchElementException(message)
                    edge_metrics.ability_score = 0.0
                    return edge_metrics

            #
            #  TRY EXECUTING ACTION
            #
            try:
                action.execute(self, user, element, edge_metrics)
                # Clear any error.
                edge_metrics.error = None
            except TimeoutException as e:
                logger.warning(f"Timed out performing {action} on {element}, retrying...")
                edge_metrics.error = e
            except (ElementNotInteractableException, ElementClickInterceptedException) as e:
                # The element is not clickable. Is there a popup covering it?
                logger.warning(
                    f"Could not perform {action} on {element}, not interactable, looking for a popup to dismiss...")
                if not self.try_dismiss_popup():
                    edge_metrics.error = e
                    retries = 0
            except JavascriptException as e:
                # Some JavaScript error, not sure what to do. Try scrolling into view.
                logger.warning(f"Could not perform {action} on {element}: {e}, retrying...")
                edge_metrics.error = e
            except Exception as e:
                # Some other error. Bail.
                logger.warning(f"Could not perform {action} on {element}: {e}")
                retries = 0  # Don't retry.
                edge_metrics.error = e

            #
            # TRY RETRIEVING DOM
            #

            # If additional tabs were open, go to one of the new ones
            # TODO can an action produce multiple new tabs? If so, this will change
            # the window to one of the new tabs, not necessarily the newest one. We
            # we may have to rework this if so.
            after_tabs = set(self._driver.window_handles)
            new_tab_set = after_tabs - prior_tabs
            if new_tab_set:
                new_tab = new_tab_set.pop()
                self._driver.switch_to.window(new_tab)
                # No need to do anything here since we won't be exploring the tab any further.

            try: 
                dom = self._get_dom()
                break # Successfully acted on the element and were able to retrieve the dom
            except TimeoutException as e:
                logger.warning(f"Timeout occured while retrieving DOM. Error {e}")
                logger.info(f"Attempting to restart the chrome browser and retry action.")
                # Restart the browser and set to previous state again
                self.shutdown()
                self._create_driver(self._config)
                # Reset to state before we tried action
                self.set_state(self._current_state)
            except UnexpectedAlertPresentException:
                # This is to handle the AUTHORIZED ONLY! warning on the irs.gov refund status page.
                logger.warning(f"Unexpected alert while checking dom {self._driver.current_url}... Dismissing and retrying...")
                logger.warning(f"Last action performed: {action} on "
                               f"{element}.")
                try:
                    self._driver.switch_to.alert.accept
                except NoAlertPresentException:
                    pass  # The alert already dismissed itself.
            except JavascriptException as e:
                logger.warning(f"Unable to execute javascript to retrieve DOM. Error {e}")
            except WebDriverException as e:
                logger.warning(f"Timeout occured while retrieving DOM. Error {e}")
                logger.info(f"Attempting to restart the chrome browser and retry action.")
                # Restart the browser and set to previous state again
                self.shutdown()
                self._create_driver(self._config)
                # Reset to state before we tried action
                self.set_state(self._current_state)
            except Exception as e:
                # All other exceptions. Warn and try again.
                logger.warning(f"Unexpected error: {e}")

            if retries == 0:
                logger.error(f"Could not perform {action} on {element}: Errored out.")
                edge_metrics.ability_score = 0.0
                return edge_metrics

        # Do a straight string compare. Did the dom change in any way?
        # If so, there may be an animation we should wait to finish.
        dom_changed = (dom != prev_dom)
        if dom_changed:
            # Wait for any animations to finish playing.
            self.wait_for_animation()
            # Scroll to the top of the page and freeze the element data once more.
            self.run_js("window.scrollTo(0,0);")
            self._freeze_element_data()
            # Check the state change one more time (perhaps it did change, but then went back to how
            #   it originally was).
            dom_changed = (self._get_dom() != prev_dom)
            if dom_changed:
                # If the url is the same, but the new dom doesn't have any events in it,
                # then all we did was reload this same page.
                if self._driver.current_url == prev_url and self.run_js("return document.documentElement.getAttribute('demod_events')") is None:
                    self._current_state_data = self._entry_state.data  # We reloaded the page.
                    return edge_metrics
                # Something about the dom changed, so update the state data.
                new_reachable_elements = self._calculate_reachable() if self.is_state_valid() else set()
                self._current_state_data = self._create_state_data()
                self._current_state_data.elements_to_explore = new_reachable_elements
        # else: We were able to do the action, but the dom didn't change.
        return edge_metrics

    # --
    # Helper functions
    #
    def _get_dom(self, strip=True):
        """ Return the DOM representing the currently loaded page.

        Args:
            strip: If true, strip out any changes to the DOM that have been injected by this program.

        Returns:
            The DOM as a string.
        """
        src = "return document.documentElement.outerHTML"
        
        # This fails frequently enough that we try to handle errors locally
        # if we are unable to resolve, we raise the errors upstream
        retryAttempts = 5
        while retryAttempts > 0:
            retryAttempts -= 1
            try:
                src = self._driver.execute_script(src)
                break
            except JavascriptException as e:
                time.sleep(.2)

                if retryAttempts == 0:
                    raise e
            except WebDriverException as e:
                time.sleep(.2)
                logger.error("Likely a webdriver timeout: \n" + str(e))

                if retryAttempts == 0:
                    raise e

        
        # Get rid of unicode.
        # src = src.encode('ascii', 'ignore').decode('unicode_escape')
        # Strip out any demodocus_ignore elements.
        if strip:
            src = strip_demodocus_ignore(src)
            src = collapse_newlines(src)
        return src

    def _get_xpath_for_selenium_element(self, selenium_element):
        return self.run_js(js_get_xpath + "return getXpath(arguments[0]);", selenium_element)

    def run_js(self, js, *args):
        """ Injects javascript into the page

        Args:
            js: javascript to run, as a string
            *args: any number of arguments, which can be accessed in the javascript as 'arguments[0]'

        Returns:
            The result of the javascript.
        """
        # If any of the args are Elements, convert them to Selenium WebElements.
        def _convert_args_to_elements(args):
            args = list(args)
            for i in range(0, len(args)):
                if type(args[i]) == self.Element:
                    args[i] = self.get_selenium_element(args[i])
                elif type(args[i]) in (list, set, tuple):
                    args[i] = _convert_args_to_elements(args[i])
            return args

        args = _convert_args_to_elements(args)
        try:
            return self._driver.execute_script(js, *args)
        except Exception as e:
            logger.error(
                "Error executing javascript on url: {}\n{}\nJavascript follows\n{}"
                .format(str(e), self._driver.current_url, js))
            return None

    def _freeze_element_data(self):
        """Right after doing something that could have changed page content,
        we'll inject some JavaScript to process the new content.
        Do this whenever content might have changed.
        """
        # Each element should be augmented with attributes encoding any important style traits.
        self.run_js(js_freeze_element_data)

    def _calculate_reachable(self):
        """Right after doing something that changed the dom,
        inject some JavaScript to process the new content.
        Do this whenever the dom changed.

        Returns:
            The set of elements that just became reachable.
        """
        # Each element should be augmented with attributes encoding any important style traits.
        # Returns any elements that just became reachable.
        new_reachable_elements = self.run_js(js_calculate_reachable)
        new_reachable_elements = {self._get_element(selenium_element=el) for el in new_reachable_elements}
        return new_reachable_elements

    def reset_state(self):
        """Reset some variables when the state has changed.
        """
        self._events = None  # We'll have to grab the event handlers again in case they changed.
        self._elements.clear()  # Clear any cached elements in case they changed or disappeared.

    # --
    # Utility functions for extracting elements from the page.
    #

    def _get_element(self, xpath=None, selenium_element=None, lxml_element=None):
        """Gets or creates an element of class WebAccess.Element. Can be given
        an xpath, a selenium_element, or an lxml_element. At least one of these
        must be present.

        Args:
            xpath: an xpath for locating the element.
            selenium_element: selenium WebElement object from the currently loaded page.
            lxml_element: an lxml Element from the lxml parsed DOM.

        Returns:
            An object of class WebAccess.Element.
        """

        # Get the xpath associated with this element.
        if xpath is None and selenium_element is not None:
            xpath = self._get_xpath_for_selenium_element(selenium_element)
        if xpath is None and lxml_element is not None:
            xpath = self.get_state_data().get_xpath_for_lxml(lxml_element)
        if xpath is None:
            return None  # We had no way to get the element xpath.
        
        # See if it's already cached.
        if xpath in self._elements:
            return self._elements[xpath]

        # If it wasn't in the cache, initalize a new element.
        element = self.Element()
        element.xpath = xpath
        element._selenium_element = selenium_element
        element._lxml_element = lxml_element or self.get_lxml_element(element)
        # Add it to the cache.
        self._elements[xpath] = element
        return element

    def get_elements_supporting_js_event(self, js_event_type):
        """ Retrieves all elements that are registered for this js event.

        Args:
            js_event_type: A javascript event type like click or keyup.

        Returns:
            The set of elements that have registered an event handler for this event type.
        """
        query = f'//*[@demod_{js_event_type}][@{REACHABLE_ATT_NAME}="true"]'
        els = self.query_xpath(query)
        return els

    def query_xpath(self, query, element=None, find_one=False):
        """ The WebAccess allows xpath querying to efficiently get at particular DOM elements.

        Args:
            query: xpath query
            use_lxml: will use the saved lxml tree for speed
            find_one: will return a single element if true or a list if false

        Returns:
            A set of elements, which is the result of the javascript query.
        """
        if element is not None:
            root = self.get_selenium_element(element)
        else:
            root = self._driver
        if find_one:
            try:
                return self._get_element(selenium_element=root.find_element_by_xpath(query))
            except NoSuchElementException:
                return None
        else:
            return {self._get_element(selenium_element=el) for el in root.find_elements_by_xpath(query)}

    def get_selenium_element(self, element):
        """Returns the Selenium WebElement associated with a WebAccess::Element.
        """
        if element.xpath not in self._elements:
            # We haven't seen this element before so grab it by xpath.
            element = self._get_element(element.xpath)
            try:
                element._selenium_element = self._driver.find_element_by_xpath(element.xpath)
            except NoSuchElementException:
                # This element no longer exists. Perhaps the page kept changing after we saved its state,
                #   or we're just trying to get an element that isn't on this page.
                return None
        else:
            # We have seen this element before.
            element = self._elements[element.xpath]
            # Make sure this element has a selenium_element.
            if element._selenium_element is None:
                element._selenium_element = self._driver.find_element_by_xpath(element.xpath)
            else:
                # If it does have a selenium element stored, make sure it's not stale.
                try:
                    element._selenium_element.is_enabled()
                except StaleElementReferenceException:
                    # The page has changed since we last retrieved it so get the element again.
                    try:
                        element._selenium_element = self._driver.find_element_by_xpath(element.xpath)
                    except NoSuchElementException:
                        # This element no longer exists. Perhaps the page kept changing after we saved its state,
                        #   or we're just trying to get an element that isn't on this page.
                        return None

        return element._selenium_element

    def get_lxml_element(self, element):
        """Returns the lxml Element associated with a WebAccess::Element.
        """
        if element._lxml_element is None:
            element._lxml_element = self.get_state_data().get_elements_by_xpath(element.xpath, find_one=True)
        return element._lxml_element

    # --
    # Functions used for ability scoring
    #
    def get_el_location(self, el):
        """Get pixel location of element.

        Args:
            el: selenium...WebElement representing the element to find dist to

        Returns:
            loc: location of the el on the page
        """
        x = self.get_selenium_element(el).location["x"]
        y = self.get_selenium_element(el).location["y"]
        loc = {"x": x, "y": y}

        return loc

    def get_current_location(self):
        """Get pixel location of current focus.

        Returns:
            loc: current location on the page
        """
        # switches to focused element or <body> if no element focused
        active_el = self._driver.switch_to.active_element
        # possible improvement: more advanced than active_el.location
        x = active_el.location["x"]
        y = active_el.location["y"]
        loc = {"x": x, "y": y}

        return loc

    def get_style_info(self, el):
        """ Checks that the border is of adequate size and color

        There don't seem to be hard guidelines for the outline, just that it is visible.
        To do this in measurable terms, we will use the color contrast AA (4.5:1) standard for now.

        Args:
            el: Selenium WebElement that we are checking the border of. We can assume it is focused
            when entering this function.

        Returns: True if border passes criteria, False otherwise

        """

        # Set up our styling info, what is the information someone would need to determine if this was accessible?
        style_info = {
            "border-style": None,
            "outline-style": None,
            "el-color": None,
            "el-background": None,
            "parent-background": None,
        }

        comp_styles = self.run_js(js_get_computed_outline, el)

        # If unable to execute javascript, likely due to Stale or Missing element
        if comp_styles is None:
            return None

        if comp_styles["el"] is not None:
            # Fill style info
            style_info["border-style"] = comp_styles["el"]["border"]
            style_info["outline-style"] = comp_styles["el"]["outline"]
            style_info["el-color"] = comp_styles["el"]["color"]
            style_info["el-background"] = comp_styles["el"]["background"]
            style_info["parent-background"] = comp_styles["parent"]["background"]
            return style_info

        return None

    def generate_tab_order(self, el_xpath=None):
        """Will generate the tab order for the full page.

        NOTE: This interacts with the page and could potentially change the
        state. This could happen if tabbing through the page changes content in
        some permanent way that is not undone when tabbing back to the
        originally focused element.

        This function will create a list of all elements that will
        receive tab focus as you traverse the page. In this case,
        we will not consider state changes, since we want to know 
        the exact tab order a user would get.

        Along the way we will also want to check how the tab order moves
        and if it is highlighted. Returns focus to the original element after
        getting the tab order.

        Args:
            el_xpath: None or str denoting the xpath to overwrite the active_el
                      xpath if that turns out to be "/html/body"

        Returns:
            tab_order: List of tuples containing (el_xpath, visible, ordered)
                       where visible is if a user could see the tab outline, and
                       ordered is whether the incoming tab followed the
                       consistent left to right, top to bottom
            tab_els_by_index: list of element xpaths in the order they were
                              discovered
            orig_focused_xpath: str denoting the xpath of the element that focus
                                is on when the function starts. This is
                                necessary to calculate distance scores for users

        """

        # Record the initial element focus to re-focus after tabbing (and
        #  changing current focus) and eventually save to the state_data
        orig_el = self._driver.switch_to.active_element
        orig_focused_xpath = self._get_xpath_for_selenium_element(orig_el)
        # In the case that the active element is "/html/body", use the element
        #  xpath of the element that produced this state, except for base state,
        #  which doesn't have a path
        if orig_focused_xpath == "/html/body" and el_xpath is not None:
            orig_focused_xpath = el_xpath

        self._driver.execute_script(js_focus_first_tabbable)
        self.wait_for_animation() # Have to check for animation after each focus
        
        # Get element activated by the tab above
        first_el = self._driver.switch_to.active_element

        # Add element to tab dict or list
        tab_els = dict()
        tab_els_by_index = []

        active_el = None
        recorded_tabbable = 0

        # If we find the same element or more than 200 elements stop
        while first_el != active_el and recorded_tabbable < self._max_tabs:

            if recorded_tabbable == 0:
                active_el = first_el
            
            # Record data about the active element
            xpath = self._get_xpath_for_selenium_element(active_el)

            tab_els_by_index.append(xpath)
            # We want to get the styling of the element both when it is focused and when it
            # isn't focused, since a background change may be considered valid.
            if xpath in tab_els:
                tab_els[xpath]["num_visits"] += 1
                if tab_els[xpath]["num_visits"] > self._config.NUM_REVISITS:
                    logger.warning(f"Already encountered element '{xpath}' "
                                   f"{self._config.NUM_REVISITS} times. Halting"
                                   f" web_access.generate_tab_order() due to a "
                                   f"likely keyboard trap.")
                    break
            else:
                tab_els[xpath] = {
                    "tab_place": recorded_tabbable,
                    "num_visits": 1,
                    "position": {
                        "x": active_el.location["x"],
                        "y": active_el.location["y"]
                    },
                    "unfocused_style_info": None, # Retrieved after tabbing to the next element
                    "focused_style_info": self.get_style_info(active_el),
                }

            recorded_tabbable += 1
            prev_el = active_el

            # Try to go to the next element
            try:
                active_el.send_keys(Keys.TAB)
                self.wait_for_animation()
                
                # Set active el back to the active element
                active_el = self._driver.switch_to.active_element
            except ElementNotInteractableException as e:
                # Unable to tab on this element, stop collecting tab order and return results
                logger.error(f"Found uninteractable element while generating tab order.\n {str(e)}")
                

            # Grab the styling of the element we are currently inspecting when it is unfocused
            # NOTE: This unfocused style could be problematic if:
            # 1. The element becomes hidden after tabbed off of
            # 2. Inconsistent unfocused style (style different before and after tabbed)
            tab_els[xpath]["unfocused_style_info"] = self.get_style_info(prev_el)

        # Reset the focus to the original element focused
        # TODO: May cause problems if the state was modified due to tabbing and this element no longer exists
        try:
            orig_el.send_keys("")
        except Exception as e:
            logger.warning(f"Could not tab back to original el: "
                           f"{self._get_xpath_for_selenium_element(orig_el)} "
                           f"with error:\n\t{e}")

        return tab_els, tab_els_by_index, orig_focused_xpath

    def get_tab_distance_to_el(self, el, start_xpath=None):
        # FIXME figure out how to generalize a distance metric that relies on
        #  some distance between two deque entries.
        """Gets the tab distance from the web_access's active element to any
        element on the page

        Args:
            el: selenium...WebElement representing the element to find dist to
            start_xpath: an xpath for the element to start the calculation from

        Returns:
            dist: the tab distance between the two elements
        """
        # NOTE: This could fail weirdly if tabbing to an element changes the page dom.

        # Get xpath that denotes the start position for the distance calculation
        if start_xpath is None:
            start_xpath = self._current_state_data.orig_focused_xpath
        end_xpath = el.xpath

        tab_dict = self._current_state_data.tab_dict

        # If the start element isn't in the tab order, assume index 0.
        start_index = 0 if start_xpath not in tab_dict else tab_dict[start_xpath]["tab_place"]
        if end_xpath not in tab_dict:
            return -1  # Target element is not in the tab order.
        end_index = tab_dict[end_xpath]["tab_place"]
        index1 = min(start_index, end_index)
        index2 = max(start_index, end_index)
        # Getting the min of the distance between indices, or the wrap-around
        #  index distance, since tabs can go forward or backwards
        dist = min(index2-index1, index1 + (len(tab_dict)-index2))
        if dist < 0:
            logger.warning(f"Got negative distance with index1: {index1}; "
                           f"index2: {index2}; len(tab_dict): {len(tab_dict)}")
        return dist

    def get_el_colors(self, el):
        """Gets the (el_color, el_alpha, el_background_color) of a particular
        element in the current state of the interface.

        Args:
            el: WebAccess::Element (this file) representing the element to find dist to

        Returns:
            el_color: color of el (list of [r,g,b])
            el_alpha: transparency of el_color (float: 0.0-1.0)
            el_background_color: background color of el (list of [r,g,b])
        """

        def _format_rgb_str(rgb_str):
            """convert str 'rgb(255, 255, 255)' to list [255, 255, 255]"""
            return [int(c) for c in re.sub('[^0-9,]', '', rgb_str).split(',')]

        # get all possible background colors, considering transparencies of el
        background_alpha = 0.0
        background_el = self.get_selenium_element(el)
        background_colors = []
        background_alphas = []
        while background_alpha < 1:

            # get background color and alpha
            background_color = Color.from_string(
                background_el.value_of_css_property('background-color'))
            background_color_str = background_color.rgb
            background_alpha = float(background_color.alpha)

            # record them to our list
            if background_alpha > 0:
                background_colors.append(_format_rgb_str(background_color_str))
                background_alphas.append(background_alpha)

            # getting the parent element, or breaking the loop if it doesn't exist
            try:
                background_el = background_el.find_element_by_xpath('..')
            except:
                break

        # getting one background color
        if not background_colors:
            # white background by default
            background_color_str = 'rgb(255, 255, 255)'
            el_background_color = _format_rgb_str(background_color_str)
        else:
            combined_background_color = background_colors[-1]
            for i in reversed(range(len(background_colors) - 1)):
                # combing colors based on https://stackoverflow.com/a/48343059/8466995
                for j in range(3):
                    combined_background_color[j] = (1 - background_alphas[i]) * \
                                                   combined_background_color[
                                                       j] + \
                                                   background_alphas[i] * \
                                                   background_colors[i][j]
            el_background_color = combined_background_color

        # get color of element/text
        el_color_raw = Color.from_string(self.get_selenium_element(el).
                                         value_of_css_property('color'))
        el_alpha = float(el_color_raw.alpha)
        el_color_str = el_color_raw.rgb
        el_color = _format_rgb_str(el_color_str)

        return el_color, el_alpha, el_background_color

    def reset(self):
        self.reset_state()
        self._entry_state = None
        self._current_state = None
        self._current_state_data = None

    def is_state_valid(self):
        """Returns true if this state data is okay to add to our graph.
        Example: If we want to stay in the same web domain, we can ignore states outside of it. """
        return self._entry_state is None or wutils.urls_equal(self._driver.current_url, self._entry_state.data.url,
                                                              path=True, query=False, fragment=False)

    # --
    # Functions for testing
    #
    def set_page_source(self, source):
        """Sets the page source. This is only used by the tests to inject doms into the browser.

        Returns:
            True on success.
        """
        output_path = get_output_path(self._config)
        # Save to disk.
        # The pure raw dom isn't used anywhere; it's just for debugging.
        try:
            with open(output_path / "temp.html", 'w', encoding='utf-8') as fp:
                fp.write(source)
            self._driver.get(f'http://{self._config.server_ip}:{self._config.server_port}/temp.html')
            self.wait_for_stable_dom(seconds_interval=.5,  seconds_threshold=1)
            self.wait_for_animation()
            return True
        except Exception:
            return False


class ChromeWebAccess(WebAccess):
    """The ChromeWebAccess wraps up the user interface presented by the ChromeDriver."""

    USER_DATA_DIR_PREFIX = "chrome_dem"
    _user_data_dir = None

    def _create_driver(self, config):
        """See discussion at https://stackoverflow.com/a/50827853"""
        options = Options()
        # Access-specific parameters from the config.
        if getattr(config, "HEADLESS", True):
            options.add_argument("--headless")

        # Other parameters.
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-web-security")                      # Disables the same-origin policy (needed for document.write)
        options.add_argument(f"--window-size={config.WINDOW_SIZE[0]},"
                             f"{config.WINDOW_SIZE[1]}")

        # user-data-dir is required with the --disable-web-security flag in some versions of Chrome (intermittent).
        # If this begins to cause issues please see:https://stackoverflow.com/questions/3102819/disable-same-origin-policy-in-chrome
        user_data_dir_name = self._create_user_data_dir()
        options.add_argument(f'--user-data-dir={user_data_dir_name}')

        options.add_argument('--verbose')
        # https://stackoverflow.com/questions/48450594/selenium-timed-out-receiving-message-from-renderer
        options.add_argument("--disable-dev-shm-usage")                     # Needed if running from Docker to avoid memory problems
        options.add_argument("enable-automation")
        options.add_argument("--disable-infobars")
        # options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--disable-hang-monitor")                    # The Hang Monitor closes slow processes
        options.add_argument("--no-first-run")                              # Don't do any first-run tasks
        options.add_argument("--disable-default-apps")                      # Disables installation of default apps on first run.
        options.add_argument("--disable-background-networking")             # Disables systems that send requests in the background
        options.add_argument("--safebrowsing-disable-auto-update")          # Keeps safebrowsing from updating

        options.add_argument("--disable-permission-action-reporting")
        options.add_argument("--disable-permissions-api")

        # SSL-related switches
        # options.add_argument("--ssl-insecure")                            # Allows mixed secure/insecure content
        # options.add_argument("--disable-client-side-phishing-detection")  # Ignores invalid server certificates
        # options.add_argument("--allow-insecure-localhost")                # Ignores SSL/TSL errors on localhost
        # options.add_argument("--ignore-certificate-errors")               # Ignores SSL/TSL cert checking on client
        # options.add_argument("--ignore-urlfetcher-cert-requests")         # Ignores server cert requests

        self._driver = webdriver.Chrome(options=options)
        self._driver.set_page_load_timeout(15)

    def _create_user_data_dir(self):
        """ Creates temporary user data directory

        Returns:
            String path of the created directory (i.e. chrome_dem_tmp_x82d34)
        """
        self._user_data_dir = tempfile.TemporaryDirectory(prefix=f'{self.USER_DATA_DIR_PREFIX}_tmp_')
        return self._user_data_dir.name

    def get_user_data_dir_name(self):
        """" Retrieves string path of the created directory

        Returns:
            String path of the created directory (i.e. chrome_dem_tmp_x82d34)
        """
        return self._user_data_dir.name

    def shutdown(self):
        """ Adds handler for temporary directory """
        super().shutdown()

        if self._user_data_dir is not None:
            self._user_data_dir.cleanup()
            self._user_data_dir = None
