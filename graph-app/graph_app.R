"
Software License Agreement (Apache 2.0)

Copyright (c) 2020, The MITRE Corporation.
All rights reserved.

Licensed under the Apache License, Version 2.0 (the 'License');
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an 'AS IS' BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This project was developed by The MITRE Corporation.
If this code is used in a deployment or embedded within another project,
it is requested that you send an email to opensource@mitre.org in order to
let us know where this software is being used.
"

suppressPackageStartupMessages(library(shiny))
suppressPackageStartupMessages(library(visNetwork))
suppressPackageStartupMessages(library(RColorBrewer))
suppressPackageStartupMessages(library(igraph))
suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(ggplot2))
suppressPackageStartupMessages(library(argparser))
suppressPackageStartupMessages(library(tools))

# Global fields
SCREENSHOTS_AVAIL <- FALSE
STATE_FILES_AVAIL <- FALSE
POSSIBLE_ACCESSIBLE <- TRUE
LAYOUT_STR <- ""

################################################################################
# [start] Helper functions to prep data

# Get the build_user from the gml file
get_build_user <- function(filepath) {
  build_user <- ""
  con = file(filepath, "r")
  while ( TRUE ) {
    line = readLines(con, n = 1)
    if (grepl("buildUser", line)) {
      build_user <- substr(line, 14, nchar(line) - 1)
      break
    }
  }
  close(con)
  
  return(build_user)
}

# Get os
#   copied from http://conjugateprior.org/2015/06/identifying-the-os-from-r/
get_os <- function(){
  sysinf <- Sys.info()
  if (!is.null(sysinf)){
    os <- sysinf['sysname']
    if (os == 'Darwin')
      os <- "osx"
  } else { ## mystery machine
    os <- .Platform$OS.type
    if (grepl("^darwin", R.version$os))
      os <- "osx"
    if (grepl("linux-gnu", R.version$os))
      os <- "linux"
  }
  tolower(os)
}

# Take an igraph object, compute network metrics on them, and return visNetwork 
create_graph <- function(metric_graph, standardized = TRUE){
  
  # Calculate various metrics
  eig <- round(eigen_centrality(metric_graph, directed = TRUE)$vector, 4)
  bet <- round(betweenness(metric_graph, directed = TRUE), 4)
  close <- round(closeness(metric_graph, mode = "all"), 4)
  deg <- round(degree(metric_graph, mode = "all"), 4)
  pr <- round(page_rank(metric_graph)$vector, 4)
  
  # Make them unit vectors
  if (standardized){
    eig_mag <- sqrt(sum(eig^2))
    if (eig_mag > 0){
      eig <- eig / eig_mag
    }
    
    bet_mag <- sqrt(sum(bet^2))
    if (bet_mag > 0){
      bet <- bet / bet_mag
    }
    
    close_mag <- sqrt(sum(close^2))
    if (close_mag > 0){
      close <- close / close_mag
    }
    
    deg_mag <- sqrt(sum(deg^2))
    if (deg_mag > 0){
      deg <- deg / deg_mag
    }
    
    pr_mag <- sqrt(sum(pr^2))
    if (pr_mag > 0){
      pr <- pr / pr_mag
    }
  }
  
  # Add them to the graph object
  metric_graph <- set_vertex_attr(metric_graph, 'eigenvector', value = eig)
  metric_graph <- set_vertex_attr(metric_graph, 'betweenness', value = bet)
  metric_graph <- set_vertex_attr(metric_graph, 'closeness', value = close)
  metric_graph <- set_vertex_attr(metric_graph, 'degree', value = deg)
  metric_graph <- set_vertex_attr(metric_graph, 'pagerank', value = pr)
  
  # Convert to visNetwork graph
  visnet <- toVisNetworkData(metric_graph)
  return(visnet)
}

# Creates nodes and edges tables from a visNetwork object
to_nodes_edges <- function(visnet){
  
  nodes <- visnet$nodes

  # Pull user models
  individual_users <- names(nodes)[grep("User",names(nodes))]
  individual_users <- individual_users[!grepl(pattern = ".*\\AddScore", individual_users) & !grepl(pattern = ".*\\MultScore", individual_users)]
  
  # Format data for the original edges
  edges <- visnet$edges
  edges$id <- 1:nrow(edges)
  edges$arrows <- "to"
  edges$title <- ""
  for (i in 1:nrow(edges)){
    title_str <- paste0("id: ", edges$id[i], "<br>",
                        "action: ", edges$action[i], "<br>",
                        "users: ")
    for (individual_user in individual_users){
      if (edges[i, individual_user] > 0){
        title_str <- paste0(title_str, individual_user, " (", 
                            toString(round(edges[i, individual_user],3)),
                            "), ")
      }
    }
    title_str <- substr(title_str, 1, nchar(title_str) - 2)
    title_str <- paste0(title_str, "<br>",
                        "element: ",edges$element[i])
    edges$title[i] <- title_str
    
  }
  
  # Format data for the aggregated edges
  agg_edges <- unique(edges[,c('from','to')])
  agg_edges[individual_users] <- ""
  agg_edges$id <- c((nrow(nodes) + 1):(nrow(agg_edges) + nrow(nodes)))
  agg_edges$action_count <- 1
  for (individual_user in individual_users){
    agg_edges[, paste0(individual_user, "_max_score")] <- 0
  }
  for (i in 1:nrow(agg_edges)){
    from <- agg_edges$from[i]
    to <- agg_edges$to[i]
    sub_edges <- edges[edges$from == from & edges$to == to,]
    agg_edges[i,"action_count"] <- nrow(sub_edges)
    users_list <- list()
    for (individual_user in individual_users){
      agg_edges[i, individual_user] <- any(as.logical(sub_edges[,individual_user]))
      for (j in 1:nrow(sub_edges)){
        if (sub_edges[j, individual_user] > 0){
          agg_edges[i, paste0(individual_user, "_max_score")] <- max(sub_edges[j, individual_user], agg_edges[i, paste0(individual_user, "_max_score")])
          if (is.null(users_list[[individual_user]])){
            users_list[individual_user] <- c(sub_edges[j,"action"])
          } else{
            users_list[[individual_user]] <- c(users_list[[individual_user]], sub_edges[j,"action"])
          }
        }
      }
    }
    if (nrow(sub_edges) < 4){
      agg_edges[i, "title_verbose"] <- paste0(sub_edges$title, collapse = "<br><br>")
    } else{
      agg_edges[i, "title_verbose"] <- paste0(c(sub_edges$title[1:3],"..."), collapse = "<br><br>")
    }
    agg_edges[i, "title_verbose_all"] <- gsub("<br>", "\n", paste0(sub_edges$title, collapse = "<br><br>"))
    # Wraps text at no more than 60 characters
    agg_edges[i, "title_actions"] <- paste(strwrap(paste0(sub_edges$action, collapse = ", "), 60), collapse = "<br>")
    agg_edges[i, "title_users"] <- paste0(names(users_list), collapse = ", ")
    actions_users_str <- c()
    for (individual_user in names(users_list)){
      actions_users_str <- c(actions_users_str, paste0(individual_user, ":<br>", paste0(users_list[[individual_user]], collapse = ", ")))
    }
    agg_edges[i, "title_actions_users"] <- paste0(actions_users_str, collapse = "<br><br>")
  }
  agg_edges$arrows <- "to"
  nodes
  nodes$shape <- "dot"
  nodes$shape[as.logical(nodes$stub)] <- "square"
  
  return(list(nodes, agg_edges, edges))
}
# [end] Helper functions to get data in the necessary form
################################################################################

################################################################################
# [start] App server function
server <- function(input, output, session) {
  output$network_proxy_nodes <- renderVisNetwork({
    # Initialize default variables
    directed <- TRUE

    # Plotting fields for the nodes
    nodes$title <- paste0('id: ', nodes[,'id'] - 1)
    nodes$title <- paste0(nodes$title, '<br>', 'Stub State: ', nodes[,'stub'])
    nodes$label <- nodes[,'id'] - 1
    nodes$shadow <- TRUE 
    nodes$borderWidth <- 1
    nodes$color.border <- 'slategrey'
    nodes$color.highlight.background <- 'white'
    nodes$color.highlight.border <- "slategrey"
    
    # Plotting fields for the edges
    edges.color.map <- list()
    if(directed){
      edges$arrows <- "to" # arrows: 'from', 'to', or 'middle'
    }
    
    # If pre-computed layout is specified, render graph with that layout
    if (paste0("x_",LAYOUT_STR) %in% names(nodes)){
      layout_mat <- 10000*data.matrix(nodes[,c(paste0("x_", LAYOUT_STR), 
                                               paste0("y_", LAYOUT_STR))])
      v <- visNetwork(nodes, edges) %>%
        visIgraphLayout(layout = "layout.norm", layoutMatrix = layout_mat) %>%
        visOptions(highlightNearest = list(enabled = TRUE, degree = list(from = 0, to = 1),
                                           labelOnly = FALSE, hover = FALSE)) %>%
        addFontAwesome() %>%
        visPhysics(barnesHut = list(gravitationalConstant = 0, springConstant = 0,springLength = 0))%>%
        visEdges( smooth = list("type" = "curvedCW", roundness = 0.1))%>%
        visEvents(click = "function(nodes){
                  Shiny.onInputChange('click', {nodes: nodes.nodes[0], edges : nodes.edges[0]});
                  ;}"
        )
    # No layout specified -- using default hierarchical tree layout
    } else {
      v <- visNetwork(nodes, edges) %>%
        visIgraphLayout(layout = "layout_as_tree", smooth = TRUE, flip.y = FALSE) %>%
        visOptions(highlightNearest = list(enabled = TRUE, degree = list(from = 0, to = 1),
                                           labelOnly = FALSE, hover = FALSE, algorithm = "hierarchical")) %>%  
        addFontAwesome() %>%
        visPhysics(barnesHut = list(gravitationalConstant = 0, springConstant = 0,springLength = 0))%>%
        visEdges( smooth = list("type" = "curvedCW", roundness = 0.1))%>%
        visEvents(click = "function(nodes){
                  Shiny.onInputChange('click', {nodes: nodes.nodes[0], edges : nodes.edges[0]});
                  ;}"
        )
    }
    
    updateSelectInput(session, 'size', selected = 'pagerank')
    updateSelectInput(session, 'color', selected = individual_users[2])
    v
  })
  
  observeEvent({input$color 
                input$size
                input$tooltip
                input$edgeWidth}, ({
    print('(change nodes color)')
    colorVar <- input$color
    if (input$size == 'sum path score'){
      sizeVar <- paste0(input$color, 'AddScore')
    } else if (input$size == 'product path score'){
      sizeVar <- paste0(input$color, 'MultScore')
    } else {
      sizeVar <- input$size
    }

    # Coloring the nodes
    # allows predefined standard colors or assigns them new ones based on the levels of the colorVar
    ncols <- 2
    clevels <- 0
    eclevels <- 0
    acceptable.colors <- colors()[!grepl("\\d", colors())]
    acceptable.colors[length(acceptable.colors) + 1] <- 'silver'
    title <- colorVar
    colorVar <- input$color
    
    # Fixing hover and IDs of nodes
    size.type <- class(nodes[,sizeVar])
    nodes$title <- paste0(colorVar, ': ',nodes[,colorVar])
    nodes$title <- paste0(nodes$title, '<br>', sizeVar, ': ',nodes[,sizeVar])
    nodes$title <- paste0(nodes$title, '<br>', "Stub State: ", nodes[,"stub"])
    nodes$label <- nodes$id - 1
    
    # adjusting edge width based on user's choice
    if (input$edgeWidth == "num_actions"){
      edges$width <- 0.75+2*(edges$action_count - min(edges$action_count))/(max(edges$action_count) - min(edges$action_count))
    } else if (input$edgeWidth == "max_score") {
      score_col <- edges[,paste0(colorVar, "_max_score")]
      edges$width <- 0.75+2*score_col
    }
    if (length(unique(edges$width)) == 1){
      edges$width <- 2.75
    }
    
    ### [start] node color block
    # colors the node backgrounds based on if they are accessible or not for a specific user
    if (all(unique(nodes[,colorVar]) %in% acceptable.colors)){
      nodes$color.background <- nodes[,colorVar]
    } else{
      clevels <- unique(nodes[,colorVar])
      if(length(clevels) > 10){
        stop('Too many levels on colorVar. Please ensure you have less than 11 colors')
      } else {
        
        nodes$color.background <- factor(nodes[,colorVar])
        
        # Using 2 custom colorblind friend colors
        levels(nodes$color.background) <- rev(c("#1E88E5", "#D81B60")[1:length(clevels)])
      }
    }
    legend.list <- list()
    color.map <- unique(nodes[,c('color.background',colorVar)])
    for (i in 1:nrow(color.map)){
      legend.list[[i]] <- list(label = color.map[,colorVar][i], shape = "icon", 
                               icon = list(code = "f111", size = 25, color = color.map[,"color.background"][i]))
    }
    ### [end] node color block
    
    ### [start] edge color block
    # greys out edges that are not traversable for the specific user
    if (input$color %in% individual_users){
      displayed_edges <- edges[edges[,input$color] == TRUE,]
      displayed_ids <- displayed_edges$id
      displayed_idx <- match(displayed_ids, edges$id)
      edges$color <- "#ededed"
      edges$color[displayed_idx] <- "#545454"
    } else{
      displayed_idx <- c(1:nrow(edges))
    }
    edges$title <- edges[,paste0('title_',input$tooltip)]
    ### [end] edge color block
    
    ### [start] size block
    # changes the size of the nodes based on the metric selected
    if (size.type == 'numeric' | size.type == 'integer'){
      nodes$title <- paste0(colorVar, ': ',nodes[,colorVar])
      nodes$title <- paste0(nodes$title, '<br>', sizeVar, ': ',nodes[,sizeVar])
      nodes$title <- paste0(nodes$title, '<br>', "Stub State: ", nodes[,"stub"])
      if (length(unique(nodes[,sizeVar])) > 1){ 
        maxSize <- max(nodes[,sizeVar])
        minSize <- min(nodes[,sizeVar])
        nodes$size <- 15*(nodes[,sizeVar] - minSize)/(maxSize - minSize) + 15
      } else{
        nodes$size <- 20
      }
    } else{
      stop(paste0('The sizeVar variable cannot be of type "',size.type,'". Please select a different variable or leave it blank.'))
    }
    # plot a histogram of the metric of the nodes
    if (max(nodes[,sizeVar]) == min(nodes[,sizeVar])){
      plot_title <- 'All values the same for this metric'
      showNotification(paste0("All values are equal for ", sizeVar, ". No histogram is displayed."), type = "error", duration = 4)
    } else{
      plot_title <- sizeVar
    }
    output$histplot<-renderPlot({
      ggplot(nodes, aes_string(x=sizeVar)) + 
        geom_histogram(color="black", fill="white") + 
        ggtitle(plot_title)
    })
    ### [end] size block
    
    visNetworkProxy("network_proxy_nodes") %>%
      visUpdateNodes(nodes) %>%
      visRemoveEdges(edges$id) %>%
      visUpdateEdges(edges)
  }))
  
  output$info <- renderText({
    if (length(input$click) == 1){
      paste0("", edges[edges$id == input$click,]$title_verbose_all)
    } else{
      paste0("Click on an edge!")
    }
  })
  
  observeEvent({input$click}, 
    ({
      print('(node/edge click)')
      if (POSSIBLE_ACCESSIBLE && input$nodeClick == "statesIf" && length(input$click) == 2 && input$color != buildUser){
        new_state_col <- paste0("NewStates", substr(input$color, 1, nchar(input$color) - 4))
        if (nodes[input$click$nodes,new_state_col] != "[]"){
          color_acc_nodes <- TRUE
        } else{
          color_acc_nodes <- FALSE
        }
        states_to_color <- fromJSON(nodes[input$click$nodes,new_state_col])
        states_to_color <- sapply(states_to_color, function(v) return(v + 1))
        colorVar <- input$color
        if (input$size == 'sum path score'){
          sizeVar <- paste0(input$color, 'AddScore')
        } else if (input$size == 'product path score'){
          sizeVar <- paste0(input$color, 'MultScore')
        } else {
          sizeVar <- input$size
        }
        
        # coloring the nodes
        # allows predefined standard colors or assigns them new ones based on the levels of the colorVar
        ncols <- 2
        clevels <- 0
        eclevels <- 0
        acceptable.colors <- colors()[!grepl("\\d", colors())]
        acceptable.colors[length(acceptable.colors) + 1] <- 'silver'
        title <- colorVar
        colorVar <- input$color
        
        size.type <- class(nodes[,sizeVar])
        nodes$title <- paste0(colorVar, ': ',nodes[,colorVar])
        nodes$title <- paste0(nodes$title, '<br>', sizeVar, ': ',nodes[,sizeVar])
        nodes$title <- paste0(nodes$title, '<br>', "Stub State", ': ',nodes[,"stub"])
        nodes$label <- nodes$id - 1
        
        if (all(unique(nodes[,colorVar]) %in% acceptable.colors)){
          nodes$color.background <- nodes[,colorVar]
        } else{
          clevels <- unique(nodes[,colorVar])
          if(length(clevels) > 10){
            stop('Too many levels on colorVar. Please ensure you have less than 11 colors')
          } else {
            
            nodes$color.background <- factor(nodes[,colorVar])
            
            # Using 2 custom colorblind friend colors
            levels(nodes$color.background) <- rev(c("#1E88E5", "#D81B60")[1:length(clevels)])
            if (color_acc_nodes){
              levels(nodes$color.background) <- c(levels(nodes$color.background), "#FFC107")
              nodes$color.background[states_to_color] <- "#FFC107"
            }
          }
        }
        
        visNetworkProxy("network_proxy_nodes") %>%
          visUpdateNodes(nodes) 
      }
    }))
  
  output$status_for_click <- renderUI({ 
    if (input$nodeClick == "openSTATE"){
      if (SCREENSHOTS_AVAIL){
        "Opening screenshots"
      } else if (STATE_FILES_AVAIL){
        "Opening state files"
      } else{
        "!!! No state files or screenshots !!!"
      }
    } else if (input$nodeClick == "statesIf") {
      paste0("Accessibility analyzed: ", toString(POSSIBLE_ACCESSIBLE))
    } else{
      paste0("")
    }
  })
  
  output$state_render <- renderUI({
    if (input$nodeClick == "openSTATE") {
      if (length(input$click) == 2){
        state_preview_fpath <- ''
        if (SCREENSHOTS_AVAIL){
          state_preview_fpath <- paste0(file.path(dirname(graph_fpath),'screenshots','state'),'-',toString(input$click$nodes-1),'.png')
        }
        else if (STATE_FILES_AVAIL){
          fpath_ext <- file_ext(list.files(file.path(dirname(graph_fpath),'states'))[1])
          state_preview_fpath <- paste0(file.path(dirname(graph_fpath),'states','state'),'-',toString(input$click$nodes-1),'.',fpath_ext)
        }
        if (state_preview_fpath != ''){
          if (get_os() == "osx"){
            system2("open", state_preview_fpath)
          } else if (get_os() == "linux"){
            system2("xdg-open", state_preview_fpath)
          } else {
            shell(paste0("start ", state_preview_fpath))
          }
        }
      }
    }
    ""
  })
}
# [end] App server function
################################################################################

################################################################################
# [start] App UI function

get_ui <- function(individual_users, node_sizes, states_accessible_through,
                   open_state){

  ui <- fluidPage(
    tags$head(
      tags$style(
        HTML(".shiny-notification {
             position:fixed;
             top: calc(0%);;
             left: calc(80%);;
             }"
            )
        )
      ),
    fluidRow(
      column(
        width = 3,
        selectInput("color", "Nodes color:", individual_users),
        selectInput("size", "Nodes size (normalized):", node_sizes),
        radioButtons("nodeClick", "Nodes Click:", choiceNames = list('Nearby States',
                                                                     HTML(states_accessible_through),
                                                                     HTML(open_state)),
                     choiceValues = list('downAS', 'statesIf', 'openSTATE')),
        radioButtons("edgeWidth", "Edge Width:", choices = list('Number of Actions' = 'num_actions', 
                                                                'Max Score' = 'max_score')),
        radioButtons("tooltip", "Edge Tooltip:", choices = list('Verbose' = 'verbose', 
                                                                    'Users Only' = 'users', 
                                                                    'Actions Only' = 'actions', 
                                                                    'Actions and Users' = 'actions_users')),
        p(strong("Complete Edge Information:")),
        conditionalPanel(TRUE,
          verbatimTextOutput("info", placeholder = TRUE),
          tags$head(tags$style("#info{font-size:12px;overflow-y:scroll; 
                               max-height: 200px; background: ghostwhite;}"))
        ),
        plotOutput("histplot", height = "300px")
      ),
      column(
        width = 9,
        htmlOutput("status_for_click"),
        visNetworkOutput("network_proxy_nodes", height = "800px"),
        htmlOutput("state_render")
      )
    )
  )

  return(ui)
}


# [end] App UI function
################################################################################


################################################################################
# [start] Main function 

# Parameters to properly run the app either from a command prompt or through an
#  interactive R shell
if(!interactive()) {
  # Running from command line
  parser <- arg_parser("Command-line tool to visualize a webpage's states",
                       hide.opts=TRUE)
  parser <- add_argument(parser, "fpath", type="character",
                         help="Filepath of the graph (.gml)")
  parser <- add_argument(parser, c("--port"), type="integer", default=8081,
                         help="Port to serve the shiny app on.")
  parser <- add_argument(parser, c("--layout"), type="character", default="",
                         help="Pre-defined layout string, like 'fr_0.2'")
  args <-parse_args(parser)
  graph_fpath <- args$fpath
  port <- args$port
  LAYOUT_STR <- gsub("0.", "", args$layout)
} else{
  # Running from interactive shell
  # NOTE: This path is replaced to a local path for the dev's convenience
  graph_fpath <- "path/to/analyzed_full_graph.gml"
  port <- 8081
}

# Load in and clean graph object
g <- read_graph(graph_fpath, format = 'gml')
buildUser <- get_build_user(graph_fpath)
visnet <- create_graph(g)
graph_dfs <- to_nodes_edges(visnet)
nodes <- graph_dfs[[1]]
edges <- graph_dfs[[2]]
orig_edges <- graph_dfs[[3]]
individual_users <- names(nodes)[grep("User",names(nodes))]
individual_users <- individual_users[!grepl(pattern = ".*\\AddScore", individual_users) & !grepl(pattern = ".*\\MultScore", individual_users)]

# Determine if state files are available
fpath_ext <- file_ext(list.files(file.path(dirname(graph_fpath),'states'))[1])
if (file.exists(paste0(file.path(dirname(graph_fpath),'states','state'),'-',toString(0),'.', fpath_ext))){
  STATE_FILES_AVAIL <- TRUE
}

# Determine if state screenshots are available
if (file.exists(paste0(file.path(dirname(graph_fpath),'screenshots','state'),'-',toString(0),'.png'))){
  SCREENSHOTS_AVAIL <- TRUE
}
# Determine if accessibility has been analyzed
for (some_user in individual_users[individual_users != buildUser]){
  if (!(paste0("NewStates", substr(some_user, 1, nchar(some_user) - 4)) %in% names(nodes))){
    POSSIBLE_ACCESSIBLE <- FALSE
  }
}

# Set colors of radio buttons
open_state <- ifelse((SCREENSHOTS_AVAIL || STATE_FILES_AVAIL), 'Open State', "<font color='red'>Open State STATE</font>")
states_accessible_through <- ifelse(POSSIBLE_ACCESSIBLE, 'States Accessible Through', "<font color='red'>States Accessible Through</font>")

# Initialize node size fields
if (POSSIBLE_ACCESSIBLE){
  node_sizes <- c('betweenness', 'closeness', 'degree', 'pagerank', 'sum path score', 'product path score')
}else{
  node_sizes <- c('betweenness', 'closeness', 'degree', 'pagerank')
}

ui <- get_ui(individual_users, node_sizes, states_accessible_through, open_state)

# Running the app
if(!interactive()) {
  # Open a browser if we are not in linux
  os <- get_os()
  if (os == "osx" || os == "windows"){
    browseURL(paste0("http://127.0.0.1:", toString(port), "/"))
  } 
  runApp(list(ui = ui, server = server), host = '0.0.0.0', port = port)
}
# [end] Main function 
################################################################################

