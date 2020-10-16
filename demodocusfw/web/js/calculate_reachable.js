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

function recurseSelfAndAllChildren(el, func) {
    // This is a generalized utility function that
    //  applies func to all children recursively, from the top down.
    //  func should accept one parameter, the element.
    func(el);
    for (var i = 0; i < el.childElementCount; i++) {
        recurseSelfAndAllChildren(el.children[i], func);
    }
}

function calculateReachable_helper(el, newReachableElements) {
    // Figure out recursively whether this element is available for interactions ("reachable").
    // (REACHABLE_ATT_NAME set at beginning of this js_calculate_reachable JavaScript block.)
    
    // Elements that the user can't interact with are by definition not reachable.
    if (el.tagName == "script" || el.tagName == "style") {
        return false;
    }
    
    styles = window.getComputedStyle(el);
    
    // (1)
    // First of all, check to see if there is some definite reason why this element and its children
    //  can't be reached.
    //
    
    // Check to see if the element is hidden.
    // This is the only case in which we know for sure that this element and its children are not reachable.
    if (styles.visibility == 'hidden' || styles.display == 'none') { 
        // If so, mark self and all children as not reachable.
        recurseSelfAndAllChildren(el, function(el){el.setAttribute(REACHABLE_ATT_NAME, false);});
        return false;
    }
    
    // (2)
    // We're not sure yet if this element is reachable.
    //  We should check to see if any of its children are reachable.
    //
    
    // Recurse on the children.
    var someChildReachable = false;
    for (var i = 0; i < el.childElementCount; i++) {
        someChildReachable |= calculateReachable_helper(el.children[i], newReachableElements);
    }
    // If one of the children is reachable, then this element is reachable.
    if (someChildReachable) {
        currReachable = true;
    }
    else {
    
        // (3)
        // None of this element's children are reachable.
        // Do some additional calculations to figure out if this element is reachable.
        //
        
        // elementFromPoint doesn't work for elements that are off the page!!
        //  We have to scroll into view.
        // TODO: Comment this in once everything is working.
        //el.scrollIntoView(true);
        bounds = el.getBoundingClientRect();
        
        // First check if width or height is zero.
        if (bounds.width == 0 || bounds.height == 0) {
            // No reachable children, and this element is too tiny to be interacted with itself.
            currReachable = false;
        }
        else {
            // Is this element covered up by something else?
            // Following https://stackoverflow.com/questions/56016115/webdrivererror-element-click-intercepted-other-element-would-receive-the-click
            
            // Adjust coordinates to get more accurate results
            // Question: Why is this block necessary? Floating point error? Web positioning weirdness?
            bleft = bounds.left + 1;
            bright = bounds.right - 1;
            btop = bounds.top + 1;
            bbottom = bounds.bottom - 1;
        
            // Make sure that the image is not totally overlapped by other elements. That is,
            //  if we test the elements in the four corners, at least one of them should be this element
            //  or a child of this element. If not, we assume it is covered by other elements.
            // Note: In the rare case that all four corners are covered but the center is not,
            //  this check will be wrong (will return false).
            if (el.contains(document.elementFromPoint(bleft, btop)) ||
                el.contains(document.elementFromPoint(bright, btop)) ||
                el.contains(document.elementFromPoint(bleft, bbottom)) ||
                el.contains(document.elementFromPoint(bright, bbottom))) {
                currReachable = true;
            }
            else {
                // The element is covered up by other elements.
                currReachable = false;
            }
        }
    }

    // (4)
    // If this element is reachable now and wasn't before,
    //  add it to the newReachableElements set.
    //
    
    prevReachable = el.getAttribute(REACHABLE_ATT_NAME) || "false"; // null if this attribute did not exist before
    if (String(prevReachable) == "false" && String(currReachable) == "true") {
        //console.log(el);
        //console.log(prevReachable);
        //console.log(el.getAttribute(REACHABLE_ATT_NAME) || "false");
        newReachableElements.add(el);
    }
    el.setAttribute(REACHABLE_ATT_NAME, currReachable);
    return currReachable;
}

function calculateReachable() {
    // Sets are faster than arrays.
    //  https://medium.com/@bretcameron/how-to-make-your-code-faster-using-javascript-sets-b432457a4a77
    newReachableElements = new Set();
    calculateReachable_helper(document.body, newReachableElements);
    return newReachableElements;
}
els = calculateReachable();
//console.log(els);
return Array.from(els);  // Have to convert to an array to pass back to Selenium.