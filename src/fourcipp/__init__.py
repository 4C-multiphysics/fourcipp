# The MIT License (MIT)
#
# Copyright (c) 2025 FourCIPP Authors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""FourCIPP."""

import sys

from loguru import logger

from fourcipp.utils.configuration import load_config

# Disable FourCIPP logging by default if desired enable it in your own project
logger.disable("fourcipp")

# Load the config
CONFIG = load_config()
# If requested in the configuration, enable logging and add a sink.
if getattr(CONFIG, "log_output_flag", False):
    # Re-enable the fourcipp logger namespace
    logger.enable("fourcipp")
    try:
        config_path = getattr(CONFIG, "log_output_path", None)
        if config_path:
            # Write to configured file and replace any existing file
            logger.add(str(config_path), mode="w", format="{time} {level} {message}")
            logger.info(f"Logging enabled to file: {config_path}")
        else:
            # No path provided: log to stdout
            logger.add(sys.stdout, format="{message}")
            logger.info("Logging enabled to stdout")
    except Exception:
        # Don't raise on import-time logging setup errors
        logger.debug("Could not set up file logging during import; continuing.")

logger.info(CONFIG)
