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

//
// This javascript encodes some styling information as attributes on the element.
// It should be run whenever a page is loaded or an event is triggered.
// When a state is saved, it is saved with this additional information.
// TODO: Profile this? Doing this for all elements on a page might be slow?
//
// Some attributes and variables used in this code:
// demod_reachable: This attribute is added to elements
//   that are available for interaction in the current state.
// other demod_ attributes: added to elements to "freeze"
//   data such as css properties and location into the dom.
//
function freezeStyles(element) {
  // Take any attributes from here that depend on css
  //  and freeze them into the dom.
  // Any computed attributes we need to know about (think about animations and state comparisons).
  styles = window.getComputedStyle(el);
  element.setAttribute('demod_width', styles['width']);
  element.setAttribute('demod_height', styles['height']);
  element.setAttribute('demod_opacity', styles['opacity']);
  element.setAttribute('demod_transform', styles['transform'].toString());
}

function freezeLocation(element) {
  // Saves the element's x and y relative to the top left of the document.
  bounds = el.getBoundingClientRect();
  scrollLeft = window.pageXOffset || document.documentElement.scrollLeft,
  scrollTop = window.pageYOffset || document.documentElement.scrollTop;
  element.setAttribute('demod_left', bounds.left + scrollLeft);
  element.setAttribute('demod_top', bounds.top + scrollTop);
}

function freezeElementData() {
  var allElements = document.evaluate('.//*[not(self::script or self::style)]', document.body, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
  for (i = 0; i < allElements.snapshotLength; i++) {
      el = allElements.snapshotItem(i);
      // Freeze the element's position and important css properties into the dom.
      // These are things we'll need to know for comparison and analysis.
      freezeStyles(el);
      freezeLocation(el);
  }
}

freezeElementData();