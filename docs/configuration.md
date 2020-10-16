# Configuration

Demodocus configuration is handled by Python configuration files, which allow a
great deal of flexibility and an extensibility mechanism. The default
configuration, `demodocusfw.config.mode_accessibility_vision_users`, will be
imported at runtime. You can localize this configuration with your own
configuration module that imports this default configuration before setting
local variable values.

Details on defining a custom/local configuration and on runtime and other
configuration variables are below.

At the end of each crawler run, if the `all` or `config` options for `REPORTS`
are enabled, the configuration variables will be written to the crawl
`OUTPUT_DIR` as `crawl_config.txt`, with the added value of `ARGV`, the
commandline used to execute the crawler. This supports recording of options for
future reference. **Note**: the format of this text file is similar to Python
but is **not** valid Python.

## Custom configuration

The crawler can be run without the `--mode` option, in which case it will use
`mode_accessibility_vision_users` as described above. To substitute another
mode, specify the Python module path to that configuration. For example, to run
the crawler with two users, one using both a keyboard and a mouse, and another
using only a keyboard, use the built-in mode `mode_accessibility`:

```bash
% python crawler.py --mode demodocusfw.config.mode_accessibility http://example.com/
```

`mode_accessibility_vision_users` is an example of a custom configuration mode,
included in the framework as an example and as a commonly used option. This mode
checks several standard accessibility criteria and uses an expanded set of
vision-enabled user-models. 

> **_NOTE:_** Our config files were designed to inherit from one another, and
each level should only contain fields that (1) have not yet been defined by an
inherited config or (2) are overwriting fields from an inherited config.
Currently, we anticipate users stacking their configs in multiple levels, ranging
from most general to most specific. While there are no hard and fast rules, we
imagine the fields and configs will typically be structured similar to below:

> 1. **General fields** such as `OUTPUT_DIR`, `REPORTS`, and `LOG_LEVEL`
> 2. **Fields specific to an interface**, such as `ACCESS_CLASS` and `HEADLESS`
> 3. **Fields specific to a crawling context**, such as `STATE_DATA`,
   `EDGE_METRICS`, and `CRAWL_USERS`
>
> For our `web` context, there is no need to overwrite the `STATE_DATA` defined
> for all `web` interfaces.
>
> Refer to the
> default config for 1. `demodocusfw/config/mode_default.py`,
the default config for 2. `demodocusfw/config/mode_web.py`,
and the default config for 3. `demodocusfw/config/mode_accessibility.py`
for more information.

The set of commonly used configuration modes included in the framework may grow
over time. `mode_reduced` was used to crawl random sites in our evaluation. This
uses the reduced and single-threaded controller, and makes sure the window is
tall enough to capture all content on most sites.

This pattern -- importing from the default mode and then setting custom values
on common variables -- can be followed with local configuration modules that a
single developer or user may use without sharing it through git. This may be
helpful during development and testing.

The path `localconfig` is included in `.gitignore`; it is recommended that you
place any personal configuration files in that directory to keep them local to
your environment.

It is also recommended to name configuration modes with the `mode_*.py`
convention, for consistency. It is possible that other aspects of configuration
may be developed with separate prefixes, such as `users_*.py` for user model
definitions, `comparator_*.py` for comparator stacks, or for different
combinations of HTML parsing and accessibility rules for testing. These can in
turn be imported into `mode_*.py` configuration files.

## Configuration variables

The description of configuration variables in
[Running crawls](running-crawls.md), along with the comments in
`demodocusfw.config.mode_default`, should provide sufficient description of each
variable. Any additional values defined in a custom configuration will be
ignored by the crawler.

For the most part, configuration variables are either defined in the config
module or as options/arguments on the crawler command line. There are two
exceptions, where an option is defined in the configuration module but may be
overridden at runtime by a commandline option:

* `OUTPUT_DIR` - for the convenience of regression testing, which generates
  temporary directories for crawler output and tests that output, `--output_dir`
  may be passed as a command line option.

* `LOG_LEVEL` - the options `--debug` and `--verbose` will override the config
  module for the convenience of development and testing.
