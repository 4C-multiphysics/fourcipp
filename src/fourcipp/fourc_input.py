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

import copy
import difflib

from loguru import logger

from fourcipp import ALL_SECTIONS, CONFIG, LEGACY_SECTIONS, SECTIONS
from fourcipp.legacy_io import (
    inline_legacy_sections,
    interpret_legacy_section,
)
from fourcipp.utils.dict_utils import compare_nested_dicts_or_lists
from fourcipp.utils.not_set import NotSet, check_if_set
from fourcipp.utils.validation import validate_using_json_schema
from fourcipp.utils.yaml_io import dump_yaml, load_yaml


class UnknownSectionException(Exception):
    """Unknown section exception."""


def is_section_known(section_name):
    """Returns if section in known.

    Does not apply to legacy sections.

    Args:
        section_name (str): Name of the section to check

    Returns:
        bool: True if section is known.
    """
    return section_name in SECTIONS or section_name.startswith("FUNCT")


class FourCInput:
    """4C inout file object."""

    known_sections = ALL_SECTIONS

    def __init__(self, sections=None):
        """Initialise object.

        Args:
            sections (dict): Sections to be added
        """
        self._sections = {}
        self._legacy_sections = {}

        if sections is not None:
            for k, v in sections.items():
                self.__setitem__(k, v)

    @classmethod
    def from_4C_yaml(cls, input_file_path, header_only=False):
        """Load 4C yaml file.

        Args:
            input_file_path (str): Path to yaml file
            header_only (bool): Only extract header, i.e., all sections except the legacy ones

        Returns:
            FourCInputFile: Initialised object
        """
        data = load_yaml(input_file_path)
        if header_only:
            for section in LEGACY_SECTIONS:
                data.pop(section, None)
        return cls(data)

    @property
    def inlined(self):
        """Get as dict with inlined legacy sections.

        Returns:
            dict: With all set sections in inline dat style
        """
        return self._sections | inline_legacy_sections(self._legacy_sections.copy())

    def __repr__(self):
        """Representation string.

        Returns:
            str: Representation string
        """
        string = "\n4C Input file"
        string += "\n with sections\n  - "
        string += "\n  - ".join(self.get_section_names()) + "\n"
        return string

    def __str__(self):
        """To string method,

        Returns:
            str: Object description.
        """
        string = "\n4C Input file"
        string += "\n with sections\n  - "
        string += "\n  - ".join(self.get_section_names()) + "\n"
        return string

    def __setitem__(self, key, value):
        """Set section.

        Args:
            key (str): Section name
            value (dict): Section entry
        """
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

    def __getitem__(self, key):
        """Get section.

        Args:
            key (str): Section name

        Returns:
            dict: Section value
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

    def pop(self, key, default_value=NotSet):
        """Pop entry.

        Args:
            key (str): Section name
            default_value (obj): Default value if section is not set

        Returns:
            obj: Desired section or default value
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

    def add(self, sections):
        """Add multiple sections from dict or FourCInput.

        Args:
            sections (dict, FourCInput): Sections to be updated
        """
        if isinstance(sections, dict):
            for k, v in sections.items():
                self[k] = v
        elif isinstance(sections, FourCInput):
            self.join(sections)
        else:
            raise TypeError(
                f"Cannot add object of type {type(sections)} to FourCInput."
            )

    @property
    def sections(self):
        """All the set sections.

        Returns:
            dict: Set sections
        """
        return self._sections | self._legacy_sections

    def get_section_names(self):
        """Get set section names.

        Returns:
            list: Sorted section names
        """
        return sorted(list(self._legacy_sections) + list(self._sections))

    def items(self):
        """Get items.

        Similar to items method of python dicts.

        Returns:
            dict_items: Dict items
        """
        return (self.sections).items()

    def __contains__(self, item):
        """Contains function.

        Allows to use the `in` operator.

        Args:
            item (string): Section name to check if it is set

        Returns:
            bool: True if section is set
        """
        return item in (list(self._legacy_sections) + list(self._sections))

    def join(self, other):
        """Join input files together.

        Args:
            other (FourCInputFile): Input file object to join
        """
        if not isinstance(other, type(self)):
            raise TypeError(f"Can not join types {type(self)} and {type(other)}")

        # Sections that can be found in both
        if doubled_defined_sections := set(self.get_section_names()) & set(
            other.get_section_names()
        ):
            raise ValueError(
                f"Section(s) {', '.join(list(doubled_defined_sections))} are defined in both {type(self).__name__} objects. In order to join the {type(self).__name__} objects remove the section(s) in one of them."
            )

        # Add the section from other
        for key, value in other.items():
            self[key] = value

    def __add__(self, other):
        """Add two input file objects together.

        In contrast to `join` a copy is created.

        Args:
            other (FourCInputFile): Input file object to join.

        Returns:
            FourCInputFile: Joined input file
        """
        copied_object = self.copy()
        copied_object.join(other)
        return copied_object

    def copy(self):
        """Copy itself.

        Returns:
            FourCInputFile: Copy of current object
        """
        return copy.deepcopy(self)

    def load_includes(self):
        """Load data from the includes section."""
        if includes := self.pop("INCLUDES", None):
            for partial_file in includes:
                logger.debug(f"Gather data from {partial_file}")
                self.join(self.from_4C_yaml(partial_file))

    def dump(self, input_file_path, sort_sections=False, validate=False):
        """Dump object to yaml.

        Args:
            input_file_path (str): Path to dump the data to
            sort_sections (bool): Sort the sections alphabetically
            validate (bool): Validate input data before dumping
        """

        if validate:
            self.validate()

        dump_yaml(self.inlined, input_file_path, sort_sections)

    def validate(self, json_schema=CONFIG["json_schema"]):
        """Validate input file.

        Args:
            json_schema (dict): Schema to check the data
        """
        return validate_using_json_schema(self.inlined, json_schema)

    def split(self, section_names):
        """Split input into two using sections names.

        Args:
            section_names (list): List of sections to split

        Returns:
            tuple: root and split input objects
        """
        root_input = self.copy()
        spiltted_input = FourCInput()

        for section in section_names:
            spiltted_input[section] = root_input.pop(section)

        return root_input, spiltted_input

    def dump_with_includes(
        self,
        section_names,
        root_input_file_path,
        split_input_file_path,
        invert_sections=False,
        sort_sections=False,
        validate=False,
    ):
        """Dump input and split using the includes function.

        Args:
            section_names (list): List of sections to split
            root_input_file_path (str): Directory with the INCLUDES section
            split_input_file_path (str): Remaining sections
            invert_sections (bool): Switch sections in root and split file
            sort_sections (bool): Sort the sections alphabetically
            validate (bool): Validate input data before dumping
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

    def __eq__(self, other):
        """Define equal operator.

        This comparison is strict, if tolerances are desired use `compare`.

        Args:
            other (FourCInput): Other input to check
        """
        if not isinstance(other, type(self)):
            raise TypeError(f"Can not compare types {type(self)} and {type(other)}")

        return self.sections == other.sections

    def compare(
        self,
        other,
        allow_int_as_float=False,
        rtol=1.0e-5,
        atol=1.0e-8,
        equal_nan=False,
        raise_exception=False,
    ):
        """Compare inputs with tolerances.

        Args:
            other (FourCInput): Input to compare
            allow_int_as_float (bool): Allow the use of ints instead of floats
            rtol (float): The relative tolerance parameter for numpy.isclose
            atol (float): The absolute tolerance parameter for numpy.isclose
            equal_nan (bool): Whether to compare NaN's as equal for numpy.isclose
            raise_exception (bool): If true raise exception

            Returns:
                bool: True if within tolerance
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

    def extract_header(self):
        """Extract the header sections, i.e., all non-legacy sections.

        Returns:
            FourCInput: Input with only the non-legacy sections
        """
        return FourCInput(sections=self._sections)
