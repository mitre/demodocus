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

// Look for elements with event handlers as attributes like: <button onclick=js()/>
// When the whole page is loaded, go back and look at attributes. (Can't figure out how else to do this yet.)
function demod_collectEventAttributes() {
  // Get all items with an event attribute.
  // Which is faster, one xpath query or several?
  // Use the following line to get all elements with event listeners at once.
  //xpath = "//*[@" + demod_eventTypes.join(" or @") + "]";
  // For each event type, get all the elements that have that event type.
  for (let eventType of demod_eventTypes) {
      let xpath = "//*[@on" + eventType + "]";
      let res = document.evaluate(xpath, document.body, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
      for (let nodeIndex = 0; nodeIndex < res.snapshotLength; nodeIndex++) {
          demod_addEventListener(res.snapshotItem(nodeIndex), eventType);
      }
  }
}
demod_collectEventAttributes();