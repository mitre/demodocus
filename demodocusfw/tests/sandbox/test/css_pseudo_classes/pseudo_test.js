// Given a rule, finds all elements the rule applies to
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

    let splitSelectors = rule.selectorText.split(',');
    let selectors = []

    for (selector of splitSelectors) {
        let pseudoIndex = selector.indexOf(pseudoClass);

        // Not all selectors within a rule may have the pseudo class
        if (pseudoIndex === -1) continue;

        let remainingSelector = selector.substr(pseudoIndex);

        // We consider the activator selector to be found when we find a space ' '
        // and the parenthesis count is 0. An example for why is below
        // e.g., .hover:hover:not(.someclass > a) p
        let selectorEndIndex = pseudoIndex; // Starting where the pseudo class is
        let parenCount = 0;
        for (c of remainingSelector) {
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

        // E.g., Input: .classname:pseudo:not(#id) p -> .classname:not(#id)
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
    start = cssRule.cssText.indexOf('{');
    end = cssRule.cssText.lastIndexOf('}');
    style = cssRule.cssText.substr(start + 1, end - start - 1);
    return style
}

// Returns all elements that have css rules attached to them with the given pseudoclass.
function demod_findPseudoRules(pseudoClass) {
    const stylesToCheck = ["display", "opacity", "background", "transform", "width", "height"];
    let pseudoRules = [];
    for (sheet of document.styleSheets) {
        let rules = [...sheet.rules];
        for (let index = 0; index < rules.length; index++) {
            let rule = rules[index];
            // For media rules that use @media, for now we will disregard them
            if (rule instanceof CSSMediaRule) {
                // Add the rules underneath this condition for consideration
                rules = rules.concat([...rule.cssRules]);
                continue; // This rule doesn't need to be considered for addition
            }

            if ("selectorText" in rule && rule.selectorText.indexOf(':' + pseudoClass) >= 0) {
                containsStyle = false;
                for (style of stylesToCheck) {
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
    for (rule of rules) {
        pseudoRulesInfo.push({
            'rule': rule,
            'style': demod_getStyleFromRule(rule), // Some css style e.g., color: red;
            'selectors': demod_parseSelectors(rule, pseudoClass) // Array of selectors
            // see demod_parseSelectors function for notes
        });
    }

    return pseudoRulesInfo;
}

let pseudoRulesInfo = demod_getPseudoRulesInfo('hover');
let head = document.getElementsByTagName('head')[0];
let demod_style = document.createElement('style');
demod_style.type = 'text/css';
head.append(demod_style);

let globalCounter = 0;
for (rule of pseudoRulesInfo) {

    console.log("Adding rule", rule);

    // The local counter will lose reference each loop, but
    // be maintained in the event handlers for use in finding the correct
    // class for styling
    let localCounter = globalCounter;
    demod_style.sheet.addRule('.demodocus-' + localCounter, rule['style']);

    for (selector of rule['selectors']) {
        // We always must have activator elements
        let activatorEl = [...document.querySelectorAll(selector['activatorText'])];

        for (act of activatorEl) {

            let appliedEl = null;
            // Used to create the unique selector below. We like to use the parent of act
            // to run the query selector since we have to do less work ourselves. However, we
            // need to ensure that the parent doesn't have two children that fit the same selector
            act.setAttribute('demod_active', 'true');
            let css_selector = selector['activatorText'] + '[demod_active="true"] ' + selector['appliedText'];

            // Find elements that the styling should be applied to 
            appliedEl = [...act.parentNode.querySelectorAll(css_selector)];

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
