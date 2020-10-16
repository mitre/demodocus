# Demodocus Graph App

This repo is used to visualize the networks created by `demodocus`.

**note:** the terms `graph` and `network` are used interchangeably.
They represent how different states are connected.

## Installation

### Docker Installation 

It is recommended to install and run the graph visualization with `Docker`. If
you wish to change the CRAN mirror, please edit the line in the `Dockerfile`
before you run `docker build ...`:

```R
                           repos='http://cran.rstudio.com/')"
```

With an [up-to-date Docker install](https://docs.docker.com/get-docker/), run
the lines below to build the image. **NOTE**: The initial build will take a few
minutes to complete. 

```bash
% cd demodocus-framework/graph-app
% docker build -t demodocus-graph-app:latest .
```

To test that this worked properly, try the example file:

```bash
% docker run -v /absolute/path/to/demodocus-framework/graph-app/example_crawl_output:/usr/src/crawl_output \
             -p 8081:8081 demodocus-graph-app:latest \
             Rscript --vanilla graph_app.R crawl_output/analyzed_full_graph.gml
```

---

**NOTE** `-p` publishes the port from the container to the host system, which
allows us to see use the web app on the host machine. The container port should
always be `8081`, but if you wish to map to a different port on the host
machine, change this call to `-p <host-port>:8081`. 

---

And visit http://0.0.0.0:8081 on your host machine. You should be able to
interact with the graph.

If you installed the graph app with Docker, skip directly to [Usage](#usage).

### Local R / Manual Installation

This repo has been built and tested with **R version 4.0.0**. You can install R
from a variety of mirrors. Many people also install [R Studio](https://www.rstudio.com/products/rstudio/download/#download)
as an IDE. 

In order run R from the command line, you will need to add the executables to
your `path` environment variable. For windows, the executables are usually
located here: `C:\Program Files\R\R-4.0.0\bin`. Test that this worked by running
the following lines:

```bash
% Rscript
```

If you primarily use R Studio, your user installed packages may not be
accessible to command-line R. Include this environment variable in Windows:
`R_LIBS = C:\Users\<user>\Documents\R\win-library\4.0`. Be sure to check that
the path works for you before setting this variable. You can test it by running
the following lines:

```bash
% R # start interactive R shell
> .libPaths()
```

and

```bash
% Rscript
```

The following packages are needed: 

* `shiny`
* `ggplot2`
* `igraph`,
* `visNetwork`
* `RColorBrewer`
* `jsonlite`
* `tools`
* `argparser`

In an R shell, you can install them with this command:

```bash
% R # start interactive R shell
> install.packages(c('shiny', 'ggplot2', 'igraph', 'visNetwork', 'RColorBrewer', 'jsonlite', 'tools', 'argparser'))
```

To test that this worked properly, try the example file:

**Windows:**
```bash
% Rscript --vanilla graph_app.R example_crawl_output\analyzed_full_graph.gml
```

**Unix/Linux:**
```bash
% Rscript --vanilla graph_app.R example_crawl_output/analyzed_full_graph.gml
```

## Usage

To run an interactive app that displays the graph and plots various metrics, go
to the command line and run the following:

**Windows:**
```bash
% Rscript --vanilla graph_app.R path\to\output_dir\full_graph.gml
```

**Unix/Linux:**
```bash
% Rscript --vanilla graph_app.R path/to/output_dir/full_graph.gml
```

---

**NOTE** if you installed this using `Docker`, the call above needs to exist
at the end of the `docker run` command (below). An equivalent command is:

---

```bash
% docker run -v /absolute/path/to/output_dir:/usr/src/crawl_output -p 8081:8081 \
             demodocus-graph-app:latest \
             Rscript --vanilla graph_app.R crawl_output/full_graph.gml
```

This should return a localhost URL that can be copy and pasted into any web
browser.

The **first positional argument** (required) is the filepath to the `.gml` file
(ex: `path/to/output_dir/full_graph.gml`). This is generated as a result of a
`demodocus` accessibility crawl. You can also use `analyzed_full_graph.gml`,
which allows the user to click on a inaccessible (red) node to see the other 
nodes that might become accessible if originally clicked node were accessible.

`-p`/`--port` (optional) is the desired port to host the app on (ex: `8081`).
Specify any port you like, but it may fail if there is something already running
on that port. If you don't specify a port, the app will default to `8081`.

`-l`/`--layout` (optional) is for a pre-computed network layout (ex: `fr_0.2`).
Analyzed `gml` files will have two types of layouts, namely `fr`
([Fruchterman Reingold](https://networkx.github.io/documentation/stable/reference/generated/networkx.drawing.layout.spring_layout.html))
and `kk` ([Kamada Kawai](https://networkx.github.io/documentation/stable/reference/generated/networkx.drawing.layout.kamada_kawai_layout.html)).
This allows nodes that share the same origin node to be closer to each other in
the rendered layout, in hopes that states discovered by elements near each other
on the page will be near each other in the graph representation. In addition to 
`0.2` in `fr_0.2`, try any other option (`0.0`, `0.4`, `0.6`, and `0.8`). Higher
numbers denote a lesser importance of the element spatial proximity.

## In-App Features

Below is a list of selections/features denoted by their name in the app (from
top to bottom in the left pane):

*  **Nodes color** changes the color of the states based on the `UserModel`.
   Blue is accessible to that user and red is inaccessible. You will also notice
   that edges disappear to states that are inaccessible for the selected user.
*  **Nodes size** changes the size of the states based on a network centrality 
   metric or based on how difficult it is to traverse to that state. Smaller
   means less central or harder to get to. `sum path score` adds the estimated
   accessibility scores along a shortest path to a given state. Similarly, 
   `product path score` multiplies the estimated accessibility scores along that
   shortest path.
*  **Nodes Click** changes what happens when you click on a state.
   `Nearby States` highlights the nearby accessible states,
   `States Accessible Through` -- when clicking on an inaccessible (red) state,
   other states that might become accessible will turn yellow if the originally
   clicked state were accessible. `Open State` will open a screenshot of the
   state that is clicked on. **NOTE** this will not work if the program is run
   through Docker.
*  **Edges Width** changes the width of the edges, either with the
   `Number of Actions` on that edge, or with the `Max Score` (estimated
   accessibility) on the actions on that edge. 
*  **Edge Tooltip** changes the edge tooltip to display different information.
   Verbose edge information is always printed to the **Complete Edge
   Information** pane.
*  **(Plot)** visualizes a histogram of the metric selected in **Nodes size**.

## License

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

If this code is used in a deployment or embedded within another project,
it is requested that you send an email to opensource@mitre.org in order to
let us know where this software is being used.
