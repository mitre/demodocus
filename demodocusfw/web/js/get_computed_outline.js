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

// Gets styles that are used to determine if the focus is visible as we tab through the page
// currenlty relies only on border, though in the future you may want to take more into account

// TODO: Should we consider border-*, where * = [top, bottom, left, right]?
// Using assumption we need a full border now
function get_computed_outline(el) {
  let dict = {}; // Python can recieve objects as dictionaries
  dict["el"] = {};
  dict["parent"] = {};

  // Get comp style of current el
  let compStyle = window.getComputedStyle(el);
  dict["el"]["color"] = compStyle.getPropertyValue("color");
  dict["el"]["border"] = compStyle.getPropertyValue("border");
  dict["el"]["outline"] = compStyle.getPropertyValue("outline");
  dict["el"]["border-top"] = compStyle.getPropertyValue("border-top");
  dict["el"]["border-bottom"] = compStyle.getPropertyValue("border-bottom");
  dict["el"]["border-right"] = compStyle.getPropertyValue("border-right");
  dict["el"]["border-left"] = compStyle.getPropertyValue("border-left");
  dict["el"]["background"] = compStyle.getPropertyValue("background");

  // Get background of parent to compare outline to
  compStyle = window.getComputedStyle(el.parentNode);
  dict["parent"]["background"] = compStyle.getPropertyValue("background");

  return dict;
}
return get_computed_outline(arguments[0]);