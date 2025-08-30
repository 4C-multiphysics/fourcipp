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
"""4C input file handler."""

from __future__ import annotations

import copy
import difflib
import pathlib
from collections.abc import Sequence
from typing import Any

from loguru import logger

from fourcipp import CONFIG
from fourcipp.legacy_io import (
    inline_legacy_sections,
    interpret_legacy_section,
)
from fourcipp.utils.converter import Converter
from fourcipp.utils.dict_utils import compare_nested_dicts_or_lists
from fourcipp.utils.not_set import NotSet, check_if_set
from fourcipp.utils.typing import Path
from fourcipp.utils.validation import ValidationError, validate_using_json_schema
from fourcipp.utils.yaml_io import dump_yaml, load_yaml

# Converter for the FourCInput
CONVERTER = Converter()


class UnknownSectionException(Exception):
    """Unknown section exception."""


def is_section_known(section_name: str, known_section_names: list[str]) -> bool:
    """Returns if section in known.

    Does not apply to legacy sections.

    Args:
        section_name: Name of the section to check
        known_section_names: Names of known sections

    Returns:
        True if section is known.
    """
    return section_name in known_section_names or section_name.startswith("FUNCT")


class FourCInput:
    """4C inout file object."""

    # All known sections
    all_sections_names: list[str] = CONFIG.sections.all_sections

    # Legacy sections, these are not supported in the 4C JSON schema
    legacy_sections_names: list[str] = CONFIG.sections.legacy_sections

    # All sections for which the types are known, aka, non-legacy
    typed_sections_names: list[str] = CONFIG.sections.typed_sections

    type_converter: Converter = CONVERTER

    def convert_to_native_types(self) -> None:
        """Convert all sections to native Python types."""
        self._sections: dict = self.type_converter(self._sections)
        self._legacy_sections: dict = self.type_converter(self._legacy_sections)

    def __init__(
        self,
        sections: dict | None = None,
    ) -> None:
        """Initialise object.

        Args:
            sections: Sections to be added
        """
        self._sections = {}
        self._legacy_sections = {}

        if sections is not None:
            for k, v in sections.items():
                self.__setitem__(k, v)

    @classmethod
    def from_4C_yaml(
        cls, input_file_path: Path, header_only: bool = False
    ) -> FourCInput:
        """Load 4C yaml file.

        Args:
            input_file_path: Path to yaml file
            header_only: Only extract header, i.e., all sections except the legacy ones

        Returns:
            Initialised object
        """
        data = load_yaml(input_file_path)
        if header_only:
            for section in cls.legacy_sections_names:
                data.pop(section, None)
        return cls(data)

    @property
    def inlined(self) -> dict:
        """Get as dict with inlined legacy sections.

        Returns:
            dict: With all set sections in inline dat style
        """
        return self._sections | inline_legacy_sections(
            self._legacy_sections.copy(), self.legacy_sections_names
        )

    def __repr__(self) -> str:
        """Representation string.

        Returns:
            str: Representation string
        """
        string = "\n4C Input file"
        string += "\n with sections\n  - "
        string += "\n  - ".join(self.get_section_names()) + "\n"
        return string

    def __str__(self) -> str:
        """To string method,

        Returns:
            str: Object description.
        """
        string = "\n4C Input file"
        string += "\n with sections\n  - "
        string += "\n  - ".join(self.get_section_names()) + "\n"
        return string

    def __setitem__(
        self,
        key: str,
        value: Any,
    ) -> None:
        """Set section.

        Args:
            key: Section name
            value: Section entry
        """
        value = self.type_converter(value)
        # Warn if complete section is overwritten
        if key in self.sections:
            logger.warning(f"Section {key} was overwritten.")
        # Nice sections
        if is_section_known(key, self.typed_sections_names):
            self._sections[key] = value
        # Legacy sections
        elif key in self.legacy_sections_names:
            # Is a list needs to be interpreted to dict
            if isinstance(value, list):
                if not any([isinstance(v, dict) for v in value]):
                    logger.debug(f"Interpreting section {key}")
                    self._legacy_sections[key] = interpret_legacy_section(
                        key, value, self.legacy_sections_names
                    )
                else:
                    # Sections are in dict form
                    self._legacy_sections[key] = value
            elif isinstance(value, dict):
                self._legacy_sections[key] = value
            else:
                raise TypeError(f"Section {key} is not a list or dict.")

        else:
            # Fancy error message
            raise UnknownSectionException(
                f"Unknown section '{key}'. Did you mean "
                f"'{difflib.get_close_matches(key.upper(), self.all_sections_names, n=1, cutoff=0.3)[0]}'?"
                " Call FourCInputFile.known_sections for a complete list."
            )

    def __getitem__(self, key: str) -> Any:
        """Get section.

        Args:
            key: Section name

        Returns:
            Section value
        """
        # Nice sections
        if is_section_known(key, self.typed_sections_names):
            return self._sections[key]
        # Legacy sections
        elif key in self._legacy_sections:
            return self._legacy_sections[key]
        else:
            sections = "\n - ".join(self.get_section_names())
            raise UnknownSectionException(
                f"Section '{key}' not set. Did out mean '{difflib.get_close_matches(key.upper(), self.all_sections_names, n=1, cutoff=0.3)[0]}'? The set sections are:\n - {sections}"
            )

    def pop(self, key: str, default_value: Any = NotSet) -> Any:
        """Pop entry.

        Args:
            key: Section name
            default_value: Default value if section is not set

        Returns:
            Desired section or default value
        """
        # Section is set
        if key in self._sections:
            return self._sections.pop(key)
        elif key in self._legacy_sections:
            return self._legacy_sections.pop(key)
        # Section is not set
        else:
            # Known section
            if key in self.all_sections_names:
                # Default value was provided
                if check_if_set(default_value):
                    return default_value
                # Default value was not provided
                else:
                    raise UnknownSectionException(
                        f"Section '{key}' not set. Did out mean '{difflib.get_close_matches(key.upper(), self.get_section_names(), n=1, cutoff=0.3)[0]}'?"
                    )
            # Unknown section
            else:
                raise UnknownSectionException(
                    f"Unknown section '{key}'. Did you mean "
                    f"'{difflib.get_close_matches(key.upper(), self.all_sections_names, n=1, cutoff=0.3)[0]}'?"
                    " Call FourCInputFile.known_sections for a complete list."
                )

    def combine_sections(self, other: dict | FourCInput) -> None:
        """Combine input files together.

        Note: Every section can only be defined in self or in other.

        Args:
            other: Sections to be combined
        """
        other_sections_names: Any = None

        if isinstance(other, dict):
            other_sections_names = other.keys()
        elif isinstance(other, FourCInput):
            other_sections_names = other.get_section_names()
        else:
            raise TypeError(
                f"Cannot combine sections between {type(self)} and {type(other)}."
            )

        # Sections that can be found in both
        if doubled_defined_sections := set(self.get_section_names()) & set(
            other_sections_names  # type: ignore
        ):
            raise ValueError(
                f"Section(s) {', '.join(list(doubled_defined_sections))} are defined in both {type(self).__name__} objects. In order to join the {type(self).__name__} objects remove the section(s) in one of them."
            )

        self.overwrite_sections(other)

    def overwrite_sections(self, other: dict | FourCInput) -> None:
        """Overwrite sections from dict or FourCInput.

        This function always overwrites complete sections. Combining parameters within
        sections has to be done manually.


        Args:
            other: Sections to be updated
        """
        if isinstance(other, (dict, FourCInput)):
            for key, value in other.items():
                self[key] = value
        else:
            raise TypeError(f"Cannot overwrite sections from {type(other)}.")

    def apply_user_defaults(
        self, default_path: Path | None = CONFIG.user_defaults_path
    ) -> None:
        """Combines two Inputs by overwriting current values by a file
        containing user defaults.

        This function checks whether values exist in both objects and overwrites the current by the other.
        At this time only top level section parameters of simple types (int, float, str, bool, None) are supported.

        Args:
            default_path: String containing the path to the YAML file with user defaults
        """
        if default_path is None:
            raise ValueError(f"User defaults path is not set in the config: {CONFIG}")
        logger.info(f"Applying user defaults from '{default_path}''.")
        user_defaults_path = pathlib.Path(default_path)
        default_input = FourCInput.from_4C_yaml(user_defaults_path, header_only=True)
        default_sections = default_input.sections

        for section_key in default_sections:
            if not isinstance(default_sections[section_key], dict):
                raise TypeError(f"Section {section_key} does not contain a dict.")
            if section_key in self.sections:
                # only check sections that are contained in the current object and in the default_sections
                for parameter_key in default_sections[section_key]:
                    if parameter_key not in self[section_key]:
                        self[section_key][parameter_key] = default_sections[
                            section_key
                        ][parameter_key]
                        logger.debug(
                            "Setting user default value {default_sections[section_key]} to parameter {parameter_key} in section {section_key}"
                        )
                        continue
                    if (
                        not isinstance(
                            self[section_key][parameter_key], (int, float, str, bool)
                        )
                        and self[section_key][parameter_key] is not None
                    ):
                        print(
                            "At this time, you should only use the default values for parameters in top level section!"
                        )
                        raise TypeError(
                            f"The value for parameter {parameter_key} in section {section_key} is not a primitive."
                        )
            else:
                # take the section content from default if it is not in the current object
                self[section_key] = default_sections[section_key]
                logger.debug(f"Adding user default section {section_key} to input file")

    @property
    def sections(self) -> dict:
        """All the set sections.

        Returns:
            dict: Set sections
        """
        return self._sections | self._legacy_sections

    def get_section_names(self) -> list:
        """Get set section names.

        Returns:
            list: Sorted section names
        """
        return sorted(list(self._legacy_sections) + list(self._sections))

    def items(self) -> Any:
        """Get items.

        Similar to items method of python dicts.

        Returns:
            dict_items: Dict items
        """
        return (self.sections).items()

    def __contains__(self, item: str) -> bool:
        """Contains function.

        Allows to use the `in` operator.

        Args:
            item: Section name to check if it is set

        Returns:
            True if section is set
        """
        return item in (list(self._legacy_sections) + list(self._sections))

    def __add__(self, other: FourCInput) -> FourCInput:
        """Add two input file objects together.

        In contrast to `join` a copy is created.

        Args:
            other: Input file object to join.

        Returns:
            Joined input file
        """
        copied_object = self.copy()
        copied_object.combine_sections(other)
        return copied_object

    def copy(self) -> FourCInput:
        """Copy itself.

        Returns:
            FourCInputFile: Copy of current object
        """
        return copy.deepcopy(self)

    def load_includes(self) -> None:
        """Load data from the includes section."""
        if includes := self.pop("INCLUDES", None):
            for partial_file in includes:
                logger.debug(f"Gather data from {partial_file}")
                self.combine_sections(self.from_4C_yaml(partial_file))

    def dump(
        self,
        input_file_path: Path,
        sort_sections: bool = False,
        validate: bool = False,
        validate_sections_only: bool = False,
        convert_to_native_types: bool = True,
    ) -> None:
        """Dump object to yaml.

        Args:
            input_file_path: Path to dump the data to
            sort_sections: Sort the sections alphabetically
            validate: Validate input data before dumping
            validate_sections_only: Validate each section independently.
                Requiredness of the sections themselves is ignored.
            convert_to_native_types: Convert all sections to native Python types
        """

        if validate or validate_sections_only:
            self.validate(
                sections_only=validate_sections_only,
                convert_to_native_types=convert_to_native_types,
            )
            # if conversion already happened in validation do not convert again
            if convert_to_native_types:
                convert_to_native_types = False

        if convert_to_native_types:
            self.convert_to_native_types()

        dump_yaml(self.inlined, input_file_path, sort_sections)

    def validate(
        self,
        json_schema: dict = CONFIG.fourc_json_schema,
        sections_only: bool = False,
        convert_to_native_types: bool = True,
    ) -> bool:
        """Validate input file.

        Args:
            json_schema: Schema to check the data
            sections_only: Validate each section independently.
                Requiredness of the sections themselves is ignored.
            convert_to_native_types: Convert all sections to native Python types
        """
        validation_schema = json_schema

        # Remove the requiredness of the sections
        if sections_only:
            validation_schema = json_schema.copy()
            validation_schema.pop("required")

        if convert_to_native_types:
            self.convert_to_native_types()

        # Validate sections using schema
        validate_using_json_schema(self._sections, validation_schema)

        # Legacy sections are only checked if they are of type string
        for section_name, section in inline_legacy_sections(
            self._legacy_sections.copy(), self.legacy_sections_names
        ).items():
            for i, k in enumerate(section):
                if not isinstance(k, str):
                    raise ValidationError(
                        f"Could not validate the legacy section {section_name}, since entry {i}:\n{k} is not a string"
                    )

        return True

    def split(self, section_names: Sequence) -> tuple[FourCInput, FourCInput]:
        """Split input into two using sections names.

        Args:
            section_names: List of sections to split

        Returns:
            root and split input objects
        """
        root_input = self.copy()
        spiltted_input = FourCInput()

        for section in section_names:
            spiltted_input[section] = root_input.pop(section)

        return root_input, spiltted_input

    def dump_with_includes(
        self,
        section_names: Sequence,
        root_input_file_path: Path,
        split_input_file_path: Path,
        invert_sections: bool = False,
        sort_sections: bool = False,
        validate: bool = False,
    ) -> None:
        """Dump input and split using the includes function.

        Args:
            section_names: List of sections to split
            root_input_file_path: Directory with the INCLUDES section
            split_input_file_path: Remaining sections
            invert_sections: Switch sections in root and split file
            sort_sections: Sort the sections alphabetically
            validate: Validate input data before dumping
        """
        # Split the inout
        first_input, second_input = self.split(section_names)

        # Select where the input should be
        if not invert_sections:
            input_with_includes = first_input
            split_input = second_input
        else:
            split_input = first_input
            input_with_includes = second_input

        # Add includes sections if missing
        if "INCLUDES" not in input_with_includes:
            input_with_includes["INCLUDES"] = []

        # Append the path to the second file
        input_with_includes["INCLUDES"].append(str(split_input_file_path))

        # Dump files
        input_with_includes.dump(root_input_file_path, sort_sections, validate)
        split_input.dump(split_input_file_path, sort_sections, validate)

    def __eq__(self, other: object) -> bool:
        """Define equal operator.

        This comparison is strict, if tolerances are desired use `compare`.

        Args:
            other: Other input to check
        """
        if not isinstance(other, type(self)):
            raise TypeError(f"Can not compare types {type(self)} and {type(other)}")

        return self.sections == other.sections

    def compare(
        self,
        other: FourCInput,
        allow_int_as_float: bool = False,
        rtol: float = 1.0e-5,
        atol: float = 1.0e-8,
        equal_nan: bool = False,
        raise_exception: bool = False,
    ) -> bool:
        """Compare inputs with tolerances.

        Args:
            other: Input to compare
            allow_int_as_float: Allow the use of ints instead of floats
            rtol: The relative tolerance parameter for numpy.isclose
            atol: The absolute tolerance parameter for numpy.isclose
            equal_nan: Whether to compare NaN's as equal for numpy.isclose
            raise_exception: If true raise exception

            Returns:
            True if within tolerance
        """
        try:
            return compare_nested_dicts_or_lists(
                other.sections, self.sections, allow_int_as_float, rtol, atol, equal_nan
            )
        except AssertionError as exception:
            if raise_exception:
                raise AssertionError(
                    "Inputs are not equal or within tolerances"
                ) from exception

            return False

    def extract_header(self) -> FourCInput:
        """Extract the header sections, i.e., all non-legacy sections.

        Returns:
            FourCInput: Input with only the non-legacy sections
        """
        return FourCInput(sections=self._sections)
