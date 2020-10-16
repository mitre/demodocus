
# Architecture - Introduction

The Demodocus Framework simulates users with different combinations of
abilities, such as using a mouse or a keyboard, and how they would move through
a given web site. Our objective is to find accessibility barriers that could
impact different users based on their abilities.

We approach this objective with this strategy:

1. Crawl the site with an "OmniUser", which can perform every action on every
   page element, to prepare a complete graph of all potential page states. Pull
   all data necessary for user models to guess if they could perform those
   actions without performing the action directly (to reduce runtime).
2. Create user-model-specific subgraphs by filtering this graph with a series
   of differential abilities to identify where certain state transitions
   (actions on elements to move from one state to another) would be difficult or
   impossible for some users. This filtering relies on data captured in step
   (1). 
3. Analyze these results to provide concrete recommendations to site developers
   to improve the accessibility of their site.

Steps 1 and 2 are described in detail in [Crawling](crawling.md).

Step 3 is described in detail in [Analysis](analysis.md).
