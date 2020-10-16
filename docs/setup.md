# Setup / Installation

We are developing and testing this framework using Python 3.8, and the following
instructions assume a clean environment (`virtualenv`, `conda env`, otherwise) for
installation. Similarly, we are using
[ChromeDriver](https://sites.google.com/a/chromium.org/chromedriver/), which
must also be present on your system.

## Installing Chromedriver

Install a
[ChromeDriver version](https://sites.google.com/a/chromium.org/chromedriver/downloads)
appropriate for your OS. The version you choose should match the version of
Chrome you have on your system, and should be updated to stay in sync whenever
Chrome itself is updated.

On a Mac using Homebrew:

```bash
% brew cask install chromedriver
```

Selenium's `WebDriver`s look for executables on `$PATH`; if chromedriver is
installed in a `$PATH` location, it should fire up just fine.

## Installing `demodocus-framework` and Dependencies

Clone this repository and navigate into it.

```bash
% git clone git@gitlab.mitre.org:demodocus/demodocus-framework.git
% cd demodocus-framework
```

Create a Python virtual environment using your environment management tool of choice,
e.g. for [pyenv](https://github.com/pyenv/pyenv), with Python 3.8 installed:

```bash
% pyenv virtualenv 3.8 py38-demodocus-framework
% pyenv local py38-demodocus-framework
```

...or with [conda](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#creating-an-environment-with-commands):

```bash
% conda create -n py38-demodocus-framework python=3.8
% conda activate py38-demodocus-framework
```

Install Python dependencies:

```bash
% pip install -r requirements.txt
```

(**not for developers**) In order to successfully import our package, please
navigate to the root directory for this repo and run:

```bash
% python setup.py install
```

(**for developers**) If you would like to be able to actively update the code,
use the `develop` option instead of the `install` option:

```bash
% python setup.py develop
```

This command will install our package `demodocusfw` so that you can import
it as you would with other python packages. 

## Testing the Installation

Open a python shell (from any directory):

```bash
% python

>>> from demodocusfw.user import UserModel
>>> UserModel
```

You should be able to see the following result with no errors:

```
<class 'demodocusfw.user.UserModel'>
```

To verify that everything is installed correctly, run one of our unit tests:

```bash
% DEM_RUN_EXTENDED=False python -m unittest demodocusfw/tests/test_crawler.py
```
