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
from collections.abc import Sequence
from typing import Any

from loguru import logger

from fourcipp import ALL_SECTIONS, CONFIG, LEGACY_SECTIONS, SECTIONS
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


class UnknownSectionException(Exception):
    """Unknown section exception."""


def is_section_known(section_name: str) -> bool:
    """Returns if section in known.

    Does not apply to legacy sections.

    Args:
        section_name: Name of the section to check

    Returns:
        True if section is known.
    """
    return section_name in SECTIONS or section_name.startswith("FUNCT")


# Converter for the FourCInput
CONVERTER = Converter()


class FourCInput:
    """4C inout file object."""

    known_sections: list = ALL_SECTIONS
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
            for section in LEGACY_SECTIONS:
                data.pop(section, None)
        return cls(data)

    @property
    def inlined(self) -> dict:
        """Get as dict with inlined legacy sections.

        Returns:
            dict: With all set sections in inline dat style
        """
        return self._sections | inline_legacy_sections(self._legacy_sections.copy())

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
        if is_section_known(key):
            self._sections[key] = value
        # Legacy sections
        elif key in LEGACY_SECTIONS:
            # Is a list needs to be interpreted to dict
            if isinstance(value, list):
                if not any([isinstance(v, dict) for v in value]):
                    logger.debug(f"Interpreting section {key}")
                    self._legacy_sections[key] = interpret_legacy_section(key, value)
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
                f"'{difflib.get_close_matches(key.upper(), ALL_SECTIONS, n=1, cutoff=0.3)[0]}'?"
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
        if is_section_known(key):
            return self._sections[key]
        # Legacy sections
        elif key in self._legacy_sections:
            return self._legacy_sections[key]
        else:
            sections = "\n - ".join(self.get_section_names())
            raise UnknownSectionException(
                f"Section '{key}' not set. Did out mean '{difflib.get_close_matches(key.upper(), ALL_SECTIONS, n=1, cutoff=0.3)[0]}'? The set sections are:\n - {sections}"
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
            if key in self.known_sections:
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
                    f"'{difflib.get_close_matches(key.upper(), ALL_SECTIONS, n=1, cutoff=0.3)[0]}'?"
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

        This function always overwrites complete sections. Combining parameters within this
        sections has to be done manually.


        Args:
            other: Sections to be updated
        """
        if isinstance(other, (dict, FourCInput)):
            for key, value in other.items():
                self[key] = value
        else:
            raise TypeError(f"Cannot overwrite sections from {type(other)}.")

    def overwrite_values(self, other: dict | FourCInput) -> None:
        """Combines two Inputs by overwriting current values by the other dict
        or FourCInput.

        This function checks whether values exist in both objects and overwrites the current by the other.

        Args:
            other: dict/FourCInput to overwrite values from.
        """

        def _check_common_keys(dict1: dict, dict2: dict) -> dict:
            """Recursive routine to check common keys/values between two
            dictionaries.

            If values are different, dict2 is the significant one to
            overrule dict1.
            """

            common_dict = {}
            for dkey in dict1:
                if dkey in dict2:
                    if type(dict1[dkey]) == dict:
                        common_dict[dkey] = _check_common_keys(dict1[dkey], dict2[dkey])
                    else:
                        common_dict[dkey] = dict2[dkey]
                else:
                    common_dict[dkey] = dict1[dkey]
            for dkey in dict2:
                if dkey in dict1:
                    continue
                common_dict[dkey] = dict2[dkey]
            return common_dict

        if isinstance(other, FourCInput):
            other_sec = other.sections
        elif isinstance(other, dict):
            other_sec = other
        else:
            raise TypeError(f"Cannot overwrite sections from {type(other)}.")

        common_dict = _check_common_keys(self.sections, other_sec)

        self.overwrite_sections(common_dict)

        return

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
        json_schema: dict = CONFIG["json_schema"],
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
            self._legacy_sections.copy()
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
