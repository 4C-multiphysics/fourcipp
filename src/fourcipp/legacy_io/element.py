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
"""Element io."""

from typing import TypeAlias

from fourcipp import CONFIG
from fourcipp.legacy_io.inline_dat import (
    _extract_vector,
    inline_dat_read,
    nested_casting_factory,
    to_dat_string,
)
from fourcipp.utils.typing import LineCastingDict

ElementCastingDict: TypeAlias = dict[str, dict[str, LineCastingDict]]


def element_data_casting_factory(
    legacy_element_specs: dict,
) -> ElementCastingDict:
    """Create element data casting dict.

    Args:
        legacy_element_specs: Element data

    Returns:
        element casting dict
    """
    elements_data_casting_dict: ElementCastingDict = {}
    for element_type, element_data in legacy_element_specs.items():
        element_type_data: dict[str, LineCastingDict] = {}

        for cell in element_data:
            element_type_data[cell["cell_type"]] = nested_casting_factory(cell["spec"])  # type: ignore[assignment]

        elements_data_casting_dict[element_type] = element_type_data

    return elements_data_casting_dict


_element_data_casting: ElementCastingDict = element_data_casting_factory(
    CONFIG.fourc_metadata["legacy_element_specs"]
)


CELL_TYPES = CONFIG.fourc_metadata["cell_types"]


def read_element(
    line: str, element_data_casting: ElementCastingDict = _element_data_casting
) -> dict:
    """Read a element line.

    Args:
        line: Inline dat description of the element
        elements_casting: Element casting dict.

    Returns:
        element as dict
    """
    line_list = line.split()

    # First entry is always the element id starting from 1
    element_id = int(line_list.pop(0))

    # Second entry is always the element type
    element_type = line_list.pop(0)

    # Third entry is the cell type
    cell_type = line_list.pop(0)

    # The next entries are the nodes of the element
    connectivity = _extract_vector(
        line_list, int, CELL_TYPES[cell_type]["number_of_nodes"]
    )

    # Element
    element = {
        "id": element_id,
        "cell": {
            "type": cell_type,
            "connectivity": connectivity,
        },
    }

    # Element data
    element["data"] = {"type": element_type} | inline_dat_read(
        line_list, element_data_casting[element_type][cell_type]
    )

    return element


def write_element(element: dict) -> str:
    """Write element as inline dat style.

    Args:
        element: Element description

    Returns:
        element line
    """
    line = " ".join(
        [
            to_dat_string(element["id"]),
            to_dat_string(element["data"]["type"]),
            to_dat_string(element["cell"]["type"]),
            to_dat_string(element["cell"]["connectivity"]),
        ]
    )
    for k, v in element["data"].items():
        if k == "type":
            continue
        line += " " + k + " " + to_dat_string(v)
    return line
