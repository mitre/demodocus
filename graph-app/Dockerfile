FROM rocker/r-base:latest

WORKDIR /usr/src

RUN R -e "install.packages(c('shiny', \
                             'visNetwork', \
                             'RColorBrewer', \
                             'igraph', \
                             'jsonlite', \
                             'ggplot2', \
                             'argparser', \
                             'tools'), \
                           dependencies=TRUE, \
                           repos='http://cran.rstudio.com/')"

COPY ./graph_app.R ./graph_app.R
