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
"""CLI utils."""

import argparse
import sys

from loguru import logger

from fourcipp.utils.configuration import (
    change_profile,
    change_user_defaults_path,
    show_config,
)


def main() -> None:
    """Main CLI interface."""
    # Set up the logger
    logger.enable("fourcipp")
    logger.remove()
    logger.add(sys.stdout, format="{message}")

    # The FourCIPP CLI is build upon argparse and subparsers. The latter ones are use to interface
    # mutual exclusive commands. If you add a new command add a new subparser and add the CLI
    # parameters as you would normally with argparse. Finally add the new command to the pattern
    # matching. More details can be found here:
    # https://docs.python.org/3/library/argparse/html#sub-commands

    main_parser = argparse.ArgumentParser(prog="FourCIPP")
    subparsers = main_parser.add_subparsers(dest="command")

    # Config parser
    subparsers.add_parser("show-config", help="Show the FourCIPP config.")

    # Switch config parser
    switch_config_profile_parser = subparsers.add_parser(
        "switch-config-profile", help="Switch user config profile"
    )
    switch_config_profile_parser.add_argument(
        "profile",
        help=f"FourCIPP config profile",
        type=str,
    )

    # Switch user defaults parser
    switch_user_defaults_path_parser = subparsers.add_parser(
        "switch-user-defaults-path", help="Switch user defaults path config profile"
    )
    switch_user_defaults_path_parser.add_argument(
        "user-defaults-path",
        help=f"FourCIPP user defaults path",
        type=str,
    )

    kwargs = vars(main_parser.parse_args(sys.argv[1:]))
    command = kwargs.pop("command")

    # Select the desired command
    match command:
        case "show-config":
            show_config()
        case "switch-config-profile":
            change_profile(**kwargs)
        case "switch-user-defaults-path":
            change_user_defaults_path(**kwargs)
