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

from typing import Callable

from fourcipp import LEGACY_SECTIONS
from fourcipp.legacy_io.domain import read_domain, write_domain
from fourcipp.legacy_io.element import read_element, write_element
from fourcipp.legacy_io.knotvectors import read_knotvectors, write_knotvectors
from fourcipp.legacy_io.node import read_node, write_node
from fourcipp.legacy_io.node_topology import read_node_topology, write_node_topology
from fourcipp.legacy_io.particle import read_particle, write_particle


def _iterate_and_evaluate(function: Callable, iterable: list) -> list:
    """Iterate through lines and evaluate function on them.

    Args:
        function: Function to be called
        iterable: List of data

    Returns:
        List evaluate as desired
    """
    return [function(line) for line in iterable]


def interpret_legacy_section(legacy_section: str, section_data: dict) -> dict | list:
    """Interpret legacy section.

    Transform line into usable data.

    Args:
        legacy_section: Section name
        section_data: Section data

    Returns:
        Interpreted data
    """
    if legacy_section not in LEGACY_SECTIONS:
        raise ValueError(
            f"Section {legacy_section} is not a known legacy section. Current legacy sections are {', '.join(LEGACY_SECTIONS)}"
        )

    match legacy_section:
        case "PARTICLES":
            return _iterate_and_evaluate(read_particle, section_data)  # type: ignore
        case "NODE COORDS":
            return _iterate_and_evaluate(read_node, section_data)  # type: ignore

        case _ if legacy_section.endswith("ELEMENTS"):
            return _iterate_and_evaluate(read_element, section_data)  # type: ignore

        case _ if legacy_section.endswith("NODE TOPOLOGY"):
            return _iterate_and_evaluate(read_node_topology, section_data)  # type: ignore

        case _ if legacy_section.endswith("DOMAIN"):
            return read_domain(section_data)  # type: ignore

        case _ if legacy_section.endswith("KNOTVECTORS"):
            return read_knotvectors(section_data)  # type: ignore

        case _:
            raise NotImplementedError(
                f"Legacy section {legacy_section} is not implemented."
            )


def interpret_legacy_sections(legacy_sections: dict) -> dict:
    """Interpret all legacy sections.

    Args:
        legacy_sections: Legacy sections and data

    Returns:
        Interpreted legacy sections
    """
    for legacy_section, section in legacy_sections.items():
        legacy_sections[legacy_section] = interpret_legacy_section(
            legacy_section, section
        )
    return legacy_sections


def inline_legacy_section(legacy_section: str, section_data: dict | list) -> list:
    """Inline legacy section.

    Transform dict form of the section into the inline dat style.

    Args:
        legacy_section: Section name
        section_data: Section data

    Returns:
        Inlined data
    """
    if legacy_section not in LEGACY_SECTIONS:
        raise ValueError(
            f"Section {legacy_section} is not a known legacy section. Current legacy sections are {', '.join(LEGACY_SECTIONS)}"
        )

    match legacy_section:
        case "PARTICLES":
            return _iterate_and_evaluate(write_particle, section_data)  # type: ignore
        case "NODE COORDS":
            return _iterate_and_evaluate(write_node, section_data)  # type: ignore

        case _ if legacy_section.endswith("ELEMENTS"):
            return _iterate_and_evaluate(write_element, section_data)  # type: ignore

        case _ if legacy_section.endswith("NODE TOPOLOGY"):
            return _iterate_and_evaluate(write_node_topology, section_data)  # type: ignore

        case _ if legacy_section.endswith("DOMAIN"):
            return write_domain(section_data)  # type: ignore

        case _ if legacy_section.endswith("KNOTVECTORS"):
            return write_knotvectors(section_data)  # type: ignore

        case _:
            raise NotImplementedError(
                f"Legacy section {legacy_section} is not implemented."
            )


def inline_legacy_sections(legacy_sections: dict) -> dict:
    """Inline all legacy sections.

    Args:
        legacy_sections: Legacy sections and data

    Returns:
        Inline legacy sections
    """

    for legacy_section, section in legacy_sections.items():
        legacy_sections[legacy_section] = inline_legacy_section(legacy_section, section)
    return legacy_sections
