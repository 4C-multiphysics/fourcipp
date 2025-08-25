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
"""Configuration utils."""

import pathlib

from loguru import logger

from fourcipp.utils.yaml_io import dump_yaml, load_yaml

CONFIG_PACKAGE: pathlib.Path = pathlib.Path(__file__).parents[1] / "config"
CONFIG_FILE: pathlib.Path = CONFIG_PACKAGE / "config.yaml"

CONFIG: dict = load_yaml(CONFIG_FILE)


def load_config() -> dict:
    """Set config profile.

    Args:
        profile: Config profile to be set.

    Returns:
        user config.
    """

    profile = CONFIG["profile"]
    logger.debug(f"Reading config profile {profile}")

    config = {"profile": profile}

    def load_yaml_for_config(config_data_name: str) -> None:
        """Load data from paths in config."""
        data = CONFIG["profiles"][profile][config_data_name + "_path"]

        if data is not None:
            if not pathlib.Path(data).is_absolute():
                # Assumption: Path is relative to FourCIPP config package
                data = CONFIG_PACKAGE / data

            config[config_data_name + "_path"] = data
            config[config_data_name] = load_yaml(data)
        else:
            logger.warning(f"Config path {config_data_name}_path was not set.")

    load_yaml_for_config("4C_metadata")
    load_yaml_for_config("json_schema")

    return config


def list_profiles() -> str:
    """List all config profiles.

    Returns:
        Fancy listing of profiles
    """
    profiles = [f"\t{k}: {v['description']}" for k, v in CONFIG["profiles"].items()]
    return "\n" + "\n".join(profiles)


def profile_description() -> str:
    """Config profile description.

    Returns:
        Fancy description
    """
    string = f"FourCIPP\n\n  with config profile {CONFIG['profile']}:"
    for k, v in CONFIG["profiles"][CONFIG["profile"]].items():
        string += f"\n   - {k}: {v}"
    string += "\n"
    return string


def change_profile(profile: str) -> None:
    """Change config profile.

    Args:
        profile: Profil name to set
    """
    logger.info(profile_description())

    if profile not in CONFIG["profiles"]:
        raise KeyError(
            f"Profile {profile} is not known provided. Known profiles are: {list_profiles()}"
        )
    CONFIG["profile"] = profile
    logger.info(f"Changing to config profile '{profile}'")
    dump_yaml(CONFIG, CONFIG_FILE)


def change_user_defaults_path(user_defaults_path: str) -> None:
    """Replace user defaults path."""
    logger.info(f"Setting user defaults path to '{user_defaults_path}'")
    CONFIG["user_defaults_path"] = user_defaults_path
    dump_yaml(CONFIG, CONFIG_FILE)


def show_config() -> None:
    """Show FourCIPP config."""
    logger.info("Fourcipp configuration")
    logger.info(f"  Config file: {CONFIG_FILE.resolve()}")
    logger.info("  Contents:")
    logger.info("    " + "\n    ".join(CONFIG_FILE.read_text().split("\n")))
