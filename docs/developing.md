# Developing

The Demodocus Framework is a Python 3 application developed both on Windows and
OS X and tested with continuous integration (CI) on RHEL. Developers should
be able to work with any of these platforms. **NOTE:** we had issues running
`demodocus` on Ubuntu Linux with some lower-level web interactions through
`selenium`. These did not appear when we tested on RHEL. 

Documentation files can be found in the `docs/` directory. Build them with
`Makefile` located in the top-level directory. 

## Continuous Integration

The Jenkins-based continuous integration environment can be deployed using the
`Jenkinsfile` located in the top-level directory. 

Gitlab CI can be deployed using the `.gitlab-ci.yml` located in the top-level
directory.

## Testing

Often when you are adding code you will want to run the unit tests. You can run
all of the tests by running (from the top-level directory) the command below.
This takes about 22 minutes on most laptops.

```bash
% python -m unittest
```

If you would like to run a specific set of tests, you can do so by running a
similar command specifying the precise tests you wish to run:

```bash
# Run all tests in test_crawler.py
% python -m unittest demodocusfw/tests/test_crawler.py

# Run single test in test_crawler.py
% python -m unittest demodocusfw.tests.TestCrawler.test_list_inaccessible_1_equivalence
```

### Extended Tests

Since the crawling tests often take a long time to run, we have our normal tests
only run on shortened examples. However, if you would like the test to be as
thorough as possible you can also run the extended tests. Below we set the
`DEM_RUN_EXTENDED` environmental variable to `True` before running the tests,
which lets our testing suite know that we would like to run on the full scale
tests. **As a forewarning**, the difference in runtime between the shortened
examples and the full tests is usually an hour or longer.

```bash
$ DEM_RUN_EXTENDED=True python -m unittest
```
