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

loc = window.location.toString().toLowerCase();
locUrl = new URL(loc);
// This JavaScript code listens for whenever an event listener is added to any element.
//  It adds the element and event listener to the demod_eventListeners dictionary.
// Here are the events we want to track.
const demod_eventTypes = ["click", "mousedown", "mouseup", "mouseover", "mouseout", "keydown", "keyup", "keypress", "focus", "blur", 
    "mouseenter", "mouseleave"];
document.documentElement.setAttribute("demod_events", "true");

function demod_addEventListener(el, type) {
    //This function is called when an event listener should be added to el.
    if (demod_eventTypes.includes(type)) {
        try {
            // Some elements have not finished loading and so won't have xpaths.
            elDesc = getXpath(el);
            if (elDesc == "") {
                elDesc = el.tagName;
            }
            console.debug("Adding " + type + " to " + elDesc);
            typeName = "demod_" + type;
            if (!(typeName in el)) {
                el[typeName] = 0;
                el.setAttribute(typeName, "" + el[typeName]);
            }
            el[typeName] += 1;
            el.setAttribute(typeName, "" + el[typeName]);
        }
        catch(e) {
            // Something you can't add attributes to... either Window or document.
        }
    }
}

function demod_removeEventListener(el, type) {
    //This function is called when an event listener should be removed from el.
    typeName = "demod_" + type;
    if (typeName in el) {
        el[typeName] -= 1;
        if (el[typeName] == 0) {
            try {
                el.removeAttribute(typeName);
                delete el[typeName];
            }
            catch(e) {
                // Something you can't add attributes to... either Window or document.
            }
        }
    }
}

/*
// TODO: Use this code block for asynchronously added nodes.
var observer = new MutationObserver(function(mutations) {
 mutations.forEach(function(mutation) {
   for (var i = 0; i < mutation.addedNodes.length; i++)
     node = mutation.addedNodes[i];
     console.debug(getXpath(node) + " added to page.");
 })
});
observer.observe(document.body, { childList: true });
*/

// Setting up for event tracking...
// Different ways an event handler can be added.

// 1) .addEventListener, and .removeEventListener
var origLisAdd = EventTarget.prototype.addEventListener;
var origLisRemove = EventTarget.prototype.removeEventListener;
EventTarget.prototype.addEventListener = function(type, handler, useCapture) {
    demod_addEventListener(this, type);
    return origLisAdd.apply(this, arguments);
}

EventTarget.prototype.removeEventListener = function(type, handler, useCapture) {
    demod_removeEventListener(this, type);
    return origLisRemove.apply(this, arguments);
}

// 2) el.onclick = X
for (i in demod_eventTypes) {
    let et = demod_eventTypes[i];
    let desc = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "on" + et);

    // WARNING: This approach has been deprecated, may need revisiting
    // See https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Object/__defineSetter__
    HTMLElement.prototype.__defineSetter__("on" + et, function(p_et, originalSet) {
        return function(f) {
            if (f == null) {
                demod_removeEventListener(this, p_et);
            }
            else {
                demod_addEventListener(this, p_et);
            }
            console.debug('setting ' + getXpath(this) + ':' + p_et + ' to ' + f);
            return originalSet.apply(this, arguments);
        };
    }(et, desc.set));
}

// TODO: Figure out how to override other sorts of event listeners.
// Maybe look at each element as it loads?