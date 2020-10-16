# Analysis

Similar to how much of the crawling code is modular and configurable to a
particular interface and/or crawling context, so is the analysis of the graph
(that is produced by crawling an application).

To analyze a graph produced by any interface and/or crawling context, use the
`demodocusfw.analysis.BaseAnalyzer`. By default, it will compare the graph of
each crawl `UserModel` to that of the build `UserModel`, both with network
metrics and optimal paths. A report is printed to the output directory called
`analysis_report.md`. An analyzed `.gml` file is also outputted, which can be
read into the graph application for visualization.

## Implementing a new `Analyzer`

The *accessibility* context required more analysis than what is generic to all
applications, and is a good example on how to implement other `Analyzer`s. See
`demodocusfw/web/accessibility/analysis.py` for more details. When building a
new `Analyzer`, you may want to perform analysis on the fully built graph (not
specific to any `UserModel`), and/or you may want to perform analysis for each
of the `UserModel`s that crawled the graph. To do this, you will need to
override the following fields and methods in `BaseAnalyzer`.

  * Fields
      * `_build_sections`
          * Stores formatting and text information for sections that run once
            per analysis
      * `_crawl_user_sections`
          * Stores formatting and text information for sections that
            run once per crawl `UserModel`

  * Methods
      * `_analyze_build()`
          * Includes analysis on sections tied to those in `_build_sections`
      * `_analyze_crawl_user()`
          * Includes analysis on sections tied to those in
            `_crawl_user_sections`

> **_NOTE:_** If you only need to make changes to just the `build` analysis,
you do not need to change **Fields** and **Methods** associated with the
`crawl_user`s, and vice versa.

If a new `Analyzer` needs access to other data, simply put that data in your
crawler configuration file. All analyzers have full access to the data in the
config using their `Analyzer.config` instance getter method.

There are many other methods that can be updated, and many that probably won't
need to be updated. For more of those details, see the high-level comments in
`demodocusfw/analyis.py::BaseAnalyzer`.
