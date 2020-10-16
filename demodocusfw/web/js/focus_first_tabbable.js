/*
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
*/

// Get first tabbable element in page, see: https://gomakethings.com/how-to-get-the-first-and-last-focusable-elements-in-the-dom/
// We have to be a bit smarter and make sure to check for positive tab indices first
function focus_first_el() {
  let focusable = document.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');

  // Check if there are any focusable elements
  if (focusable.length == 0)
  {
      return false;
  }

  // The [tabindex]:not([tabindex="-1"]) selector does not seem to work unless it is explicitly defined
  let firstFocusEl = null;
  for (element of [...focusable])
  {
      if (element.tabIndex >= 0) {
          firstFocusEl = element;
          break;
      }
  }

  if (firstFocusEl.tabIndex == 1){ // If this element has tab index 1 it is impossible for any other element to be first
      firstFocusEl.focus();
      return true;
  }

  for (element of [...focusable])
  {
      // The only way a later element takes priority is if it has a positive index that is less
      // than firstFocusEl. If firstFocusEl tab index is 0, then any positive index wins
      if (element.tabIndex > 0 && (element.tabIndex < firstFocusEl.tabIndex || firstFocusEl.tabIndex == 0)){
          firstFocusEl = element;
      }

      // We don't need to check if element.tabIndex = 0, since any value for firstFocusEl would win.
      // I.e, firstFocusEl.tabIndex must equal 0 or +int, each would take priority
  }

  firstFocusEl.focus();
  return true;
}

return focus_first_el();