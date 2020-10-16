# Analysis Report
## Contents
* [Guide](#guide)
    * [Visible Border & Tab Analysis](#guide-els_states)
    * [Summary Metrics](#guide-metrics)
    * [Path Analysis](#guide-paths)
    * [Inaccessible Elements](#guide-inacc)
* [Visible Border & Tab Analysis](#els_states)
* [VizKeyUser](#vizkeyuser)
    * [Summary Metrics](#vizkeyuser-metrics)
    * [Path Analysis](#vizkeyuser-paths)
    * [Inaccessible Elements](#vizkeyuser-inacc)
* [VizMouseKeyUser](#vizmousekeyuser)
    * [Summary Metrics](#vizmousekeyuser-metrics)
    * [Path Analysis](#vizmousekeyuser-paths)
    * [Inaccessible Elements](#vizmousekeyuser-inacc)
* [SuperVizMouseKeyUser](#supervizmousekeyuser)
    * [Summary Metrics](#supervizmousekeyuser-metrics)
    * [Path Analysis](#supervizmousekeyuser-paths)
    * [Inaccessible Elements](#supervizmousekeyuser-inacc)
* [LowVizMouseKeyUser](#lowvizmousekeyuser)
    * [Summary Metrics](#lowvizmousekeyuser-metrics)
    * [Path Analysis](#lowvizmousekeyuser-paths)
    * [Inaccessible Elements](#lowvizmousekeyuser-inacc)

## <a name="guide"></a> Guide

### <a name="guide-els_states"></a> Visible Border & Tab Analysis
 * **valid tab order** -- all elements for a crawled state (not stub state) can be navigated to via a `TAB` key (forward and backward), and follow a logical ordering (top to bottom, left to right).
 * **visual indication of focus**  -- issues occur when an element for a crawled state (not stub state) has the same focused and unfocused style information.

### <a name="guide-metrics"></a> Summary Metrics
 * **in-degree** -- number of edges that point into a given node
 * **out-degree** -- number of edges that point away from a given node
 * **strongly connected graph** -- for a given graph, a path exists between every pair of nodes (and in both directions)

### <a name="guide-paths"></a> Path Analysis
 * **path** -- an ordered series of edges that connects one node to another node
 * **path length** -- number of edges in a path
 * **average path length** -- for all paths in a graph, the average of all path lengths
 * the **paths dataframe** has the following columns:
     * **idx_from** -- index/ID of the starting node for a path
     * **idx_to** -- index/ID of the ending node for a path
     * **path_incr** -- this represents how much more the shortest path length from **idx_from** to **idx_to** is for the given user compared to the BuildUser. *Example*: a value of **2** means that it takes a given user 2 more actions to get from **idx_from** to **idx_to** than it does for BuildUser. **0** is desirable, higher numbers are not
     * **dijkstra_diff** -- this represents the difference of the shortest weighted path length (using Dijkstra's algorithm) from **idx_from** to **idx_to** for the given user compared to the BuildUser. *Example*: a value of **0.2** means that the average score for each edge in the path from **idx_from** to **idx_to** is 0.2 lower (out of 1) for the BuildUser than it is for the CrawlUser. **0** is desirable and represents ease of accessibility, higher numbers are worse

### <a name="guide-inacc"></a> Inaccessible Elements
 * any reference to a state contains a hyperlink to its corresponding `HTML` dom file

## <a name="els_states"></a> Visible Border & Tab Analysis
 * **100.0% states** (not including stub states) have a valid tab order **(5 / 5)**

 * **No elements have issues with visual indication of focus**

## <a name="vizkeyuser"></a> VizKeyUser
### <a name="vizkeyuser-metrics"></a> Summary Metrics
**80.0% states** accessible compared to BuildUser **(4 / 5)**

 * No **stub nodes** found in this graph

**60.0% edges** accessible compared to BuildUser **(12 / 20)**

**3.0** average in-degree (**4.0** for BuildUser)

**3.0** average out-degree (**4.0** for BuildUser)

strongly connected user graph: **True**
### <a name="vizkeyuser-paths"></a> Path Analysis

Average path length increase compared to BuildUser: **0.0**


Average Dijkstra difference between shortest paths compared to BuildUser: **0.17**

**First 10 rows of paths dataframe** for VizKeyUser:

|   idx_from |   idx_to |   path_incr |   dijkstra_diff |
|-----------:|---------:|------------:|----------------:|
|          0 |        2 |           0 |            0.32 |
|          0 |        3 |           0 |            0.32 |
|          1 |        2 |           0 |            0.21 |
|          1 |        3 |           0 |            0.21 |
|          2 |        3 |           0 |            0.21 |
|          3 |        2 |           0 |            0.21 |
|          0 |        1 |           0 |            0.1  |
|          1 |        0 |           0 |            0.1  |
|          2 |        0 |           0 |            0.1  |
|          2 |        1 |           0 |            0.1  |
**NOTE:** The full paths csv is also stored here: `build/crawls/20200825T204704Z/VizKeyUser_paths_df.csv`
### <a name="vizkeyuser-inacc"></a> Inaccessible Elements
**0** inaccessible elements for this user:


## <a name="vizmousekeyuser"></a> VizMouseKeyUser
### <a name="vizmousekeyuser-metrics"></a> Summary Metrics
**100.0% states** accessible compared to BuildUser **(5 / 5)**

 * No **stub nodes** found in this graph

**100.0% edges** accessible compared to BuildUser **(20 / 20)**

**4.0** average in-degree (**4.0** for BuildUser)

**4.0** average out-degree (**4.0** for BuildUser)

strongly connected user graph: **True**
### <a name="vizmousekeyuser-paths"></a> Path Analysis

Average path length increase compared to BuildUser: **0.0**


Average Dijkstra difference between shortest paths compared to BuildUser: **0.2**

**First 10 rows of paths dataframe** for VizMouseKeyUser:

|   idx_from |   idx_to |   path_incr |   dijkstra_diff |
|-----------:|---------:|------------:|----------------:|
|          0 |        4 |           0 |            0.45 |
|          0 |        2 |           0 |            0.32 |
|          0 |        3 |           0 |            0.32 |
|          1 |        4 |           0 |            0.27 |
|          2 |        4 |           0 |            0.27 |
|          3 |        4 |           0 |            0.27 |
|          1 |        2 |           0 |            0.21 |
|          1 |        3 |           0 |            0.21 |
|          2 |        3 |           0 |            0.21 |
|          3 |        2 |           0 |            0.21 |
**NOTE:** The full paths csv is also stored here: `build/crawls/20200825T204704Z/VizMouseKeyUser_paths_df.csv`
### <a name="vizmousekeyuser-inacc"></a> Inaccessible Elements
**0** inaccessible elements for this user:


## <a name="supervizmousekeyuser"></a> SuperVizMouseKeyUser
### <a name="supervizmousekeyuser-metrics"></a> Summary Metrics
**100.0% states** accessible compared to BuildUser **(5 / 5)**

 * No **stub nodes** found in this graph

**100.0% edges** accessible compared to BuildUser **(20 / 20)**

**4.0** average in-degree (**4.0** for BuildUser)

**4.0** average out-degree (**4.0** for BuildUser)

strongly connected user graph: **True**
### <a name="supervizmousekeyuser-paths"></a> Path Analysis

Average path length increase compared to BuildUser: **0.0**


Average Dijkstra difference between shortest paths compared to BuildUser: **0.2**

**First 10 rows of paths dataframe** for SuperVizMouseKeyUser:

|   idx_from |   idx_to |   path_incr |   dijkstra_diff |
|-----------:|---------:|------------:|----------------:|
|          0 |        4 |           0 |            0.45 |
|          0 |        2 |           0 |            0.32 |
|          0 |        3 |           0 |            0.32 |
|          1 |        4 |           0 |            0.27 |
|          2 |        4 |           0 |            0.27 |
|          3 |        4 |           0 |            0.27 |
|          1 |        2 |           0 |            0.21 |
|          1 |        3 |           0 |            0.21 |
|          2 |        3 |           0 |            0.21 |
|          3 |        2 |           0 |            0.21 |
**NOTE:** The full paths csv is also stored here: `build/crawls/20200825T204704Z/SuperVizMouseKeyUser_paths_df.csv`
### <a name="supervizmousekeyuser-inacc"></a> Inaccessible Elements
**0** inaccessible elements for this user:


## <a name="lowvizmousekeyuser"></a> LowVizMouseKeyUser
### <a name="lowvizmousekeyuser-metrics"></a> Summary Metrics
**100.0% states** accessible compared to BuildUser **(5 / 5)**

 * No **stub nodes** found in this graph

**100.0% edges** accessible compared to BuildUser **(20 / 20)**

**4.0** average in-degree (**4.0** for BuildUser)

**4.0** average out-degree (**4.0** for BuildUser)

strongly connected user graph: **True**
### <a name="lowvizmousekeyuser-paths"></a> Path Analysis

Average path length increase compared to BuildUser: **0.0**


Average Dijkstra difference between shortest paths compared to BuildUser: **0.2**

**First 10 rows of paths dataframe** for LowVizMouseKeyUser:

|   idx_from |   idx_to |   path_incr |   dijkstra_diff |
|-----------:|---------:|------------:|----------------:|
|          0 |        4 |           0 |            0.45 |
|          0 |        2 |           0 |            0.32 |
|          0 |        3 |           0 |            0.32 |
|          1 |        4 |           0 |            0.27 |
|          2 |        4 |           0 |            0.27 |
|          3 |        4 |           0 |            0.27 |
|          1 |        2 |           0 |            0.21 |
|          1 |        3 |           0 |            0.21 |
|          2 |        3 |           0 |            0.21 |
|          3 |        2 |           0 |            0.21 |
**NOTE:** The full paths csv is also stored here: `build/crawls/20200825T204704Z/LowVizMouseKeyUser_paths_df.csv`
### <a name="lowvizmousekeyuser-inacc"></a> Inaccessible Elements
**0** inaccessible elements for this user:

