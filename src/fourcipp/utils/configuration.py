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

from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

from loguru import logger

from fourcipp.utils.typing import Path
from fourcipp.utils.yaml_io import dump_yaml, load_yaml

CONFIG_PACKAGE: pathlib.Path = pathlib.Path(__file__).parents[1] / "config"
CONFIG_FILE: pathlib.Path = CONFIG_PACKAGE / "config.yaml"


class Sections:
    def __init__(self, legacy_sections: list[str], typed_sections: list[str]):
        """Sections data container.

        Args:
            legacy_sections: Legacy sections, i.e., their information is not provided in the schema file
            typed_sections: Typed sections, non-legacy sections natively supported by the schema
        """
        self.legacy_sections: list[str] = legacy_sections
        self.typed_sections: list[str] = typed_sections
        self.all_sections: list[str] = legacy_sections + typed_sections

    @classmethod
    def from_metadata(cls, fourc_metadata: dict) -> Sections:
        """Get section names from metadata.

        Args:
            fourc_metadata (dict): 4C metadata

        Returns:
            Sections: sections object
        """
        description_section = fourc_metadata["metadata"]["description_section_name"]
        sections = [
            section["name"] for section in fourc_metadata["sections"]["specs"]
        ] + [description_section]
        legacy_sections = list(fourc_metadata["legacy_string_sections"])

        return cls(legacy_sections, sections)


@dataclass
class ConfigProfile:
    """Fourcipp configuration profile.

    Attributes:
        name: Name of the configuration profile
        description: Description of the profile
        fourc_metadata_path: Path to metadata yaml file
        json_schema_path: Path to json schema path
        user_defaults_path: Path to user specific defaults
    """

    name: str
    description: str
    fourc_metadata_path: Path
    fourc_json_schema_path: Path
    user_defaults_path: Path | None = None
    fourc_metadata: dict = field(init=False)
    fourc_json_schema: dict = field(init=False)
    sections: Sections = field(init=False)

    def __post_init__(self) -> None:
        """Update stuff."""
        self.fourc_metadata_path = pathlib.Path(self.fourc_metadata_path)
        self.fourc_metadata = ConfigProfile._load_data_from_path(
            self.fourc_metadata_path
        )
        self.sections = Sections.from_metadata(self.fourc_metadata)

        self.fourc_json_schema_path = pathlib.Path(self.fourc_json_schema_path)
        self.fourc_json_schema = ConfigProfile._load_data_from_path(
            self.fourc_json_schema_path
        )

        if self.user_defaults_path is not None:
            self.user_defaults_path = pathlib.Path(self.user_defaults_path)
            if not self.user_defaults_path.is_file():
                raise FileNotFoundError(
                    f"User defaults file '{self.user_defaults_path}' does not exist."
                )

    @staticmethod
    def _load_data_from_path(path: Path) -> dict:
        """Load data from path."""
        if not pathlib.Path(path).is_absolute():
            # Assumption: Path is relative to FourCIPP config package
            logger.debug(
                f"Path {path} is a relative path. The absolute path is set to {CONFIG_PACKAGE / path}"
            )
            path = CONFIG_PACKAGE / path
        return load_yaml(path)

    def __str__(self) -> str:
        """String method for the config."""

        def add_keyword(name: str, data: object) -> str:
            """Create keyword description line."""
            return f"\n - {name}: {data}"

        s = f"FourCIPP configuration '{self.name}'"
        s += add_keyword("Configuration file", CONFIG_FILE)
        s += add_keyword("Description", self.description)
        s += add_keyword("4C metadata path", self.fourc_json_schema_path)
        s += add_keyword("4C JSON schema path", self.fourc_json_schema_path)
        s += add_keyword("User default path", self.user_defaults_path)

        return s


def load_config() -> ConfigProfile:
    """Set config profile.

    Args:
        profile: Config profile to be set.

    Returns:
        user config.
    """
    config_data: dict = load_yaml(CONFIG_FILE)
    profile_name = config_data["profile"]
    profile = config_data["profiles"][profile_name]
    logger.debug(f"Reading config profile {profile}")

    config = ConfigProfile(name=profile_name, **profile)
    logger.debug(config)
    return config


def change_profile(profile: str) -> None:
    """Change config profile.

    Args:
        profile: Profil name to set
    """
    config_data: dict = load_yaml(CONFIG_FILE)

    if profile not in config_data["profiles"]:
        known_profiles = ", ".join(config_data["profiles"])
        raise KeyError(
            f"Profile {profile} unknown. Known profiles are: {known_profiles}"
        )
    config_data["profile"] = profile
    logger.info(f"Changing to config profile '{profile}'")
    dump_yaml(config_data, CONFIG_FILE)


def show_config() -> None:
    """Show FourCIPP config."""
    logger.info("Fourcipp configuration")
    logger.info(f"  Config file: {CONFIG_FILE.resolve()}")
    logger.info("  Contents:")
    logger.info("    " + "\n    ".join(CONFIG_FILE.read_text().split("\n")))
