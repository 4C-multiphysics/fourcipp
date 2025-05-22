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

from fourcipp import CONFIG
from fourcipp.legacy_io.inline_dat import (
    casting_factory,
    inline_dat_read,
    to_dat_string,
)

_ELEMENT_CASTING: dict = {}
if CONFIG["4C_metadata"] is not None:
    _ELEMENT_CASTING = casting_factory(CONFIG["4C_metadata"]["legacy_element_specs"])


def read_element(line: str, elements_casting: dict = _ELEMENT_CASTING) -> dict:
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

    element_parameter_casting = elements_casting[element_type][cell_type]

    element = {
        "id": element_id,
        "cell": {
            "type": cell_type,
            "connectivity": element_parameter_casting[cell_type](line_list),
        },
        "data": {"type": element_type}
        | inline_dat_read(line_list, element_parameter_casting),
    }
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
