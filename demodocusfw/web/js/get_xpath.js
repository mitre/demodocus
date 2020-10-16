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

// Calculate xpath for a given element
function getXpath(el) {
  var result = "";
  while (el.parentNode !== undefined && el.parentNode !== null) {
      var i = 1;
      var el_index = 0;
      siblings = el.parentNode.childNodes
      for (c in siblings) {
          if (siblings[c] == el) {
              el_index = i;
          }   
          else if (siblings[c].tagName == el.tagName)
              i += 1;
      }
      if (i > 1)
          result = "/" + el.tagName + "[" + el_index + "]" + result;
      else
          result = "/" + el.tagName + result;
      el = el.parentNode;
  }
  return result.toLowerCase();
}