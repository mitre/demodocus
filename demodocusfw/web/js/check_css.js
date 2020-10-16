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

/**
 * This file contains code for tranforming all state transitions due to css into
 * javascript state transitions. For exmaple, the :hover pseudo class might be used
 * to change styling (and possibly state) of a page. Unfortunately, we don't seem to be
 * able to trigger these through normal means, so we transform them into mouseover 
 * and mouseout events.
 * 
 * DEPRECATION WARNING: We used to only use javascript events and not selenium. This
 * code may be unnecessary with the addition of selenium events, though we may still
 * need to use the below to find elements that are triggerable by these actions. 
 */


/**
* This turns out to be much trickier than one would expect due to the
* various ways that css selectors can be built. We have some implementation below
* but will be building up the robustness of this function for some time to come.
*
* @returns An object:
* {
*  "activator": // CSS selector for element that is activated by :psuedo
*   "applied": // CSS selector for elements the styles are applied to
* }
*/
function demod_parseSelectors(cssRule, pseudoClass) {

  // Find the full activator selector text
  pseudoClass = ':' + pseudoClass;

  let splitSelectors = cssRule.selectorText.split(',');
  let selectors = []

  for (let selector of splitSelectors) {
      let pseudoIndex = selector.indexOf(pseudoClass);

      // Not all selectors within a rule may have the pseudo class
      if (pseudoIndex === -1) {
          continue;
      }
      // Check for rules that use :hover as a selector
      // E.g. selector:not(:hover), selector > :hover
      else if(selector[pseudoIndex - 1] == '(' || selector[pseudoIndex - 1] == ' ' || selector[pseudoIndex - 1] == '>')
      {
          continue;
      }

      // Now we know that hover is being used and not as a selector. We need
      // to find the components of the css: activator and applied.
      //
      // The activator elements are ones that the pseudo actions triggers on,
      // and the applied elements are the ones whose styling changes as a result
      // of the trigger.
      //
      // Examples:
      // 1. .hover:hover a
      //     Activator: .hover, Applied: a
      // 2. body > div[attr="xyz"] > p.hover:hover:not(.class) a
      //     Activator: body > div[attr="xyz"] > p.hover
      //     Applied: :not(.class) a
      let remainingSelector = selector.substr(pseudoIndex);

      // We consider the activator selector to be found when we find a space ' '
      // and the parenthesis count is 0. An example for why is below
      // e.g., .hover:hover:not(.someclass > a) p
      let selectorEndIndex = pseudoIndex; // Starting where the pseudo class is
      let parenCount = 0;
      for (let c of remainingSelector) {
          if (c === '(') {
              parenCount++;
          }
          else if (c === ')') {
              parenCount--;
          }
          else if (parenCount === 0 && c === ' ') {
              break;
          }
          selectorEndIndex++;
      }

      // E.g., Input: .classname:pseudo:not(#id) p > .classname:not(#id)
      let splitActivator = selector.substr(0, selectorEndIndex).split(pseudoClass);
      let activatorText = splitActivator[0] + splitActivator[1];

      // Applied text is the selector of the elements after :pseudo
      let appliedText = selector.substr(selectorEndIndex);

      selectors.push({
          'activatorText': activatorText,
          'appliedText': appliedText,
      });
  }

  // Query selector for all of the elements
  return selectors;

}

// Gets the styling from the rule
// Currently assumes all rules are formatted in the pattern of:
// selector text { rule styles }
// We only want the rule styles
function demod_getStyleFromRule(cssRule) {
  // Simplest implementation
  let start = cssRule.cssText.indexOf('{');
  let end = cssRule.cssText.lastIndexOf('}');
  let style = cssRule.cssText.substr(start + 1, end - start - 1);
  return style
}

// Returns all elements that have css rules attached to them with the given pseudoclass.
function demod_findPseudoRules(pseudoClass) {
  const stylesToCheck = ["display", "opacity", "background", "transform", "width", "height"];
  let pseudoRules = [];
  for (let sheet of document.styleSheets) {

      // In some cases, getting rules seems to be protected. Is there a way to determine
      // this ahead of time instead of just looking for an error?
      let rules = null;
      try {
          rules = [...sheet.rules];
      }
      catch (error) {
          console.warn("Unable to get styleSheet rules:", error);
          continue;
      }

      for (let index = 0; index < rules.length; index++) {
          let rule = rules[index];
          // For media rules that use @media, we will append the sub-rules for consideration.
          if (rule instanceof CSSMediaRule) {
              // Add the rules underneath this condition for consideration
              rules = rules.concat([...rule.cssRules]);
              continue; // The sub-rules have been added for later consideration, do not consider this rule.
          }
          else if (rule instanceof CSSImportRule) {
              // For imported stylesheets, we will append the sub-rules for consideration.
              try {
                  // Some import rules won't allow to access the css rules and throw an error
                  rules = rules.concat([...rule.styleSheet.cssRules]);
              }
              catch(error) {
                  console.warn("Unable to get import rule styles:", error);
              }
              continue; // The sub-rules have been added for later consideration, do not consider this rule.
          }
// See if this rule refers to the specified pseudoclass.
          if ("selectorText" in rule && rule.selectorText.indexOf(':' + pseudoClass) >= 0) {
              let containsStyle = false;
              for (let style of stylesToCheck) {
                  if (rule.style[style] != "") {
                      containsStyle = true;
                      break;
                  }
              }

              if (containsStyle) {
                  pseudoRules.push(rule);
              }
          }
      };
  };
  return pseudoRules;
}

function demod_getPseudoRulesInfo(pseudoClass) {
  let pseudoRulesInfo = []
  let rules = demod_findPseudoRules(pseudoClass);
  for (let rule of rules) {
      let pseudoRule = {
          'rule': rule,
          'style': demod_getStyleFromRule(rule), // Some css style e.g., color: red
          'selectors': demod_parseSelectors(rule, pseudoClass) // An array of selectors using :hover
      };

      // If no selectors in the rule used :hover correctly don't add the rule
      if (pseudoRule.selectors.length > 0) {
          pseudoRulesInfo.push(pseudoRule);
      }
  }

  return pseudoRulesInfo;
}

let pseudoRulesInfo = demod_getPseudoRulesInfo('hover');
let head = document.getElementsByTagName('head')[0];
let demod_style = document.createElement('style');
demod_style.type = 'text/css';
head.append(demod_style);

// Now that we've found all the :hover rules, we need to make them trigger-able on mouseover and mouseout.
// (Simply dispatching JavaScript events does not trigger them.)
// To accomplish this, we add a number of "demodocus-n" css classes to the page, where n is an integer that 
// goes from 0 to number of classes we need.
// Then we add event listeners to the elements to add and remove these classes on mouseover and mouseout.

let globalCounter = 0;
for (let rule of pseudoRulesInfo) {

  console.log("Adding rule", rule);

  // The local counter will lose reference each loop, but
  // be maintained in the event handlers for use in finding the correct
  // class for styling
  let localCounter = globalCounter;
  demod_style.sheet.addRule('.demodocus-' + localCounter, rule.style);

  for (let selector of rule.selectors) {
      // We always must have activator elements
      let activatorEl = null;
      try {
          activatorEl = [...document.querySelectorAll(selector.activatorText)];
      }
      catch(error) {
          console.warn("Error finding activator elements:", error);
          continue;
      }

      for (let act of activatorEl) {

          let appliedEl = null;
          // Used to create the unique selector below. We like to use the parent of act
          // to run the query selector since we have to do less work ourselves. However, we
          // need to ensure that the parent doesn't have two children that fit the same selector
          // We add 'demod_active' to make sure the only element referenced by the query's selector is this one.
          act.setAttribute('demod_active', 'true');
          let css_selector = selector.activatorText + '[demod_active="true"] ' + selector.appliedText;

          // Find elements that the styling should be applied to
          try {
              appliedEl = [...act.parentNode.querySelectorAll(css_selector)];
          }
          catch (error) {
              console.warn("Unable to find applied elements", error);
              continue;
          }

          act.removeAttribute('demod_active');

          // Add mouse over and mouseout listeners that add class that points to rule style
          // this effectively simulates hover
          act.addEventListener('mouseover', () => {
              for (app of appliedEl) {
                  app.classList.add("demodocus-" + localCounter);
              }
          });

          act.addEventListener('mouseout', () => {
              for (app of appliedEl) {
                  app.classList.remove("demodocus-" + localCounter);
              }
          });
      }
  }

  globalCounter++;
}