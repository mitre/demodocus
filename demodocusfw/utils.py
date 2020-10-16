"""
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

This project was developed by The MITRE Corporation.
If this code is used in a deployment or embedded within another project,
it is requested that you send an email to opensource@mitre.org in order to
let us know where this software is being used.
"""

import logging
import os
from pathlib import Path
import shutil
import stat
import sys
from tempfile import TemporaryDirectory


# This will return the project root, that is, demodocus-framework.
ROOT_DIR = Path(os.path.abspath(__file__)).parent.parent


def get_screenshot_dir(config):
    """Given a config, returns where screenshots should go.
    Args:
        config: a config module

    Returns:
        location where screenshots should go, or None if screenshots should not be collected.
    """
    if config.SCREENSHOTS:
        return get_output_path(config, 'screenshots')
    else:
        return None


def get_output_path(config, path=None):
    """Given a config, makes and returns an output location.
    Args:
        config: a config module
        path: a new location to create in the output folder.

    Returns:
        output location
    """
    loc = Path(config.OUTPUT_DIR) if isinstance(config.OUTPUT_DIR, (str, Path)) else Path(config.OUTPUT_DIR.name)
    if path is not None:
        loc = loc / Path(path)
    os.makedirs(loc, exist_ok=True)
    return loc


def set_up_logging(log_level=logging.INFO, output_path=None, log_to_stdout=True):
    # Set up logging
    # Need to close these handlers?
    # TODO: If we just want this to apply to the demodocus loggers, we need to start all
    #   our loggers with a prefix like `demodocusfw.` and then can loop through `logging.root.manager.loggerDict`.
    #   https://stackoverflow.com/questions/54036637/python-how-to-set-logging-level-for-all-loggers-to-info
    root_logger = logging.root
    root_logger.info("Log level " + str(log_level))
    root_logger.setLevel(log_level)
    log_format = '%(asctime)s %(name)s:%(lineno)d %(levelname)s %(threadName)s %(message)s'
    if output_path is not None:
        root_logger.info("Log file " + str(output_path))
        file_handler = logging.FileHandler(filename=output_path, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)
    if log_to_stdout:
        str_handler = logging.StreamHandler(sys.stdout)
        str_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(str_handler)
        root_logger.info("Logging to stdout")


def stop_logging():
    logging.shutdown()
    logging.root.handlers.clear()


class DemodocusTemporaryDirectory:

    def __init__(self):
        self.temp_directory = TemporaryDirectory()
        self.name = self.temp_directory.name

    def __del__(self):
        self.cleanup()

    def __str__(self):
        return self.name

    def cleanup(self):
        # May cause an exception if currently still writing to a file,
        # for instance if the crawler is still writing to the log or if
        # Chrome is writing to CrashpadMetrics-active.pma.
        # Just in case, force remove all files manually.
        # https://docs.python.org/3/library/shutil.html?highlight=shutil#rmtree-example
        def handle_error(func, path, excinfo):
            etype, eValue, traceback = excinfo
            if etype == IOError or etype == PermissionError:
                # Clear the readonly bit and reattempt the removal
                os.chmod(path, stat.S_IWRITE)
                func(path)
        shutil.rmtree(self.name, onerror=handle_error)
        # Still try to clean up, but it will produce "FileNotFound" since we already deleted it.
        try:
            self.temp_directory.cleanup()
        except FileNotFoundError:
            pass


def color_contrast_ratio(fore_color, back_color):
    """Calculated the contrast ratio between a foreground color (with optional
    alpha) and a background color.

    Args:
        fore_color: Color in the form of rgb [r,g,b] or rgba [r,g,b,a]
        back_color: Color in the form of rgb [r,g,b] or rgba [r,g,b,a]

    Returns:
        Contrast ratio between the two colors
    """

    def _calculate_luminance(color_code):
        """Helper function to calculate luminance for one channel of rgb"""
        index = float(color_code) / 255

        if index < 0.03928:
            return index / 12.92
        else:
            return ((index + 0.055) / 1.055) ** 2.4

    def _calculate_relative_luminance(rgb):
        """Helper function to calculate luminance for all channels of rgb"""
        return 0.2126 * _calculate_luminance(rgb[0]) + \
               0.7152 * _calculate_luminance(rgb[1]) + \
               0.0722 * _calculate_luminance(rgb[2])

    # find which color is lighter/darker
    light = back_color if sum(back_color[0:3]) >= sum(
        fore_color[0:3]) else fore_color
    dark = back_color if sum(back_color[0:3]) < sum(
        fore_color[0:3]) else fore_color

    # compute contrast ratio
    contrast_ratio = (_calculate_relative_luminance(light) + 0.05) / \
                     (_calculate_relative_luminance(dark) + 0.05)

    # Scale by the transparency of the el
    # contrast_ratio - 1 brings the color contrast range to [0, 20] so
    # that multiplying the contrast ratio by a decimal alpha won't result
    # in a contrast ratio < 1 (which is impossible)
    if len(fore_color) == 4:
        contrast_ratio = float(fore_color[3]) * (contrast_ratio - 1) + 1

    return contrast_ratio
