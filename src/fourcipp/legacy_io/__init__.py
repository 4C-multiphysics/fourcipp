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
"""Modules related to legacy io."""

from collections.abc import Callable, Sequence

from fourcipp.legacy_io.element import read_element, write_element
from fourcipp.legacy_io.node import read_node, write_node
from fourcipp.legacy_io.node_topology import read_node_topology, write_node_topology
from fourcipp.legacy_io.particle import read_particle, write_particle
from fourcipp.utils.typing import T


def _iterate_and_evaluate(function: Callable[..., T], iterable: Sequence) -> list[T]:
    """Iterate through lines and evaluate function on them.

    Args:
        function: Function to be called
        iterable: List of data

    Returns:
        List evaluate as desired
    """
    return [function(line) for line in iterable]


def interpret_legacy_section(
    legacy_section: str, section_data: list, known_legacy_sections: list
) -> dict | list:
    """Interpret legacy section.

    Transform line into usable data.

    Args:
        legacy_section: Section name
        section_data: Section data
        known_legacy_sections: Known legacy sections

    Returns:
        Interpreted data
    """
    if legacy_section not in known_legacy_sections:
        raise ValueError(
            f"Section {legacy_section} is not a known legacy section. Current legacy sections are {', '.join(known_legacy_sections)}"
        )

    match legacy_section:
        case "PARTICLES":
            return _iterate_and_evaluate(read_particle, section_data)

        case "NODE COORDS":
            return _iterate_and_evaluate(read_node, section_data)

        case _ if legacy_section.endswith("ELEMENTS"):
            return _iterate_and_evaluate(read_element, section_data)

        case _ if legacy_section.endswith("NODE TOPOLOGY"):
            return _iterate_and_evaluate(read_node_topology, section_data)

        case _:
            raise NotImplementedError(
                f"Legacy section {legacy_section} is not implemented."
            )


def interpret_legacy_sections(
    legacy_sections: dict, known_legacy_sections: list
) -> dict:
    """Interpret all legacy sections.

    Args:
        legacy_sections: Legacy sections and data
        known_legacy_sections: Known legacy sections

    Returns:
        Interpreted legacy sections
    """
    for legacy_section, section in legacy_sections.items():
        legacy_sections[legacy_section] = interpret_legacy_section(
            legacy_section, section, known_legacy_sections
        )
    return legacy_sections


def inline_legacy_section(
    legacy_section: str, section_data: dict | list, known_legacy_sections: list
) -> list:
    """Inline legacy section.

    Transform dict form of the section into the inline dat style.

    Args:
        legacy_section: Section name
        section_data: Section data
        known_legacy_sections: Known legacy sections

    Returns:
        Inlined data
    """

    match legacy_section:
        case "PARTICLES":
            if not isinstance(section_data, Sequence):
                raise TypeError("Expected the section data to be of type list.")
            return _iterate_and_evaluate(write_particle, section_data)

        case "NODE COORDS":
            if not isinstance(section_data, Sequence):
                raise TypeError("Expected the section data to be of type list.")
            return _iterate_and_evaluate(write_node, section_data)

        case _ if legacy_section.endswith("ELEMENTS"):
            if not isinstance(section_data, Sequence):
                raise TypeError("Expected the section data to be of type list.")
            return _iterate_and_evaluate(write_element, section_data)

        case _ if legacy_section.endswith("NODE TOPOLOGY"):
            if not isinstance(section_data, Sequence):
                raise TypeError("Expected the section data to be of type list.")
            return _iterate_and_evaluate(write_node_topology, section_data)

        case _:
            raise ValueError(
                f"Section {legacy_section} is not a known legacy section. Current legacy sections are {', '.join(known_legacy_sections)}"
            )


def inline_legacy_sections(legacy_sections: dict, known_legacy_sections: list) -> dict:
    """Inline all legacy sections.

    Args:
        legacy_sections: Legacy sections and data
        known_legacy_sections: Known legacy sections

    Returns:
        Inline legacy sections
    """

    for legacy_section, section in legacy_sections.items():
        legacy_sections[legacy_section] = inline_legacy_section(
            legacy_section, section, known_legacy_sections
        )
    return legacy_sections
