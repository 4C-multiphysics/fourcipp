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
"""Test element reader and writer."""

import pytest

from fourcipp import CONFIG
from fourcipp.legacy_io.element import (
    read_element,
    write_element,
)

CELL_TYPES = CONFIG.fourc_metadata["cell_types"]
from .utils import reference_value_from_all_of


def inline_element_from_spec(element_type, cell_type, element_data_specs):
    """Generate element line from specs.

    Args:
        element_type (str): Element type
        cell_type (str): Cell type
        element_data_specs (dict): Metadata for all element data and fields

    Returns:
        str: inline element
    """
    cell_nodes = CELL_TYPES[cell_type]["number_of_nodes"]
    connectivity = "42 " * cell_nodes

    # Add additional whitespaces to check the reader
    return (
        f"42 {element_type} {cell_type} {connectivity}"
        + reference_value_from_all_of(element_data_specs)
    )


def generate_elements_from_metadatafile():
    """Generate all possible elements from metadata.

    Returns:
        list: list of inline elements
    """
    data = CONFIG.fourc_metadata["legacy_element_specs"]

    elements = []
    # Loop over element types
    for element_type, element_specs in data.items():
        # Loop over cell types
        for element_data in element_specs:
            cell_type = element_data["cell_type"]
            ele = inline_element_from_spec(
                element_type, cell_type, element_data["spec"]
            )
            elements.append(ele)
    return elements


_REFERENCE_ELEMENTS = generate_elements_from_metadatafile()


@pytest.mark.parametrize("element", _REFERENCE_ELEMENTS)
def test_elements_read_and_write(element):
    """Test elements read and write."""
    element_dict = read_element(element)
    element_line = write_element(element_dict)

    # Split into a list to account for additional whitespaces
    assert element.split() == element_line.split()
