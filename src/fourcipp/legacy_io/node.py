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
"""Node io.

Once this section is implemented in 4C using InputSpec, this file can be
simplified.
"""

from functools import partial
from typing import Callable

from fourcipp.legacy_io.inline_dat import _extract_entry, _extract_vector, to_dat_string

_FNODE_CASTING: dict[str, Callable] = {
    "CIR": partial(_extract_vector, entry_type=float, size=3),
    "TAN": partial(_extract_vector, entry_type=float, size=3),
    "RAD": partial(_extract_vector, entry_type=float, size=3),
    "HELIX": partial(_extract_entry, entry_type=float),
    "TRANS": partial(_extract_entry, entry_type=float),
}


def read_node(line: str) -> dict:
    """Read node.

    Args:
        line: Inline dat description of the element

    Returns:
        Node as dict
    """
    line_list = line.split()

    # First entry is the node type
    node_type = line_list.pop(0)

    # Second entry is the node id
    node_id = int(line_list.pop(0))

    # Read the coords
    line_list.pop(0)
    coordinate = _extract_vector(line_list, entry_type=float, size=3)

    node = {"id": node_id, "COORD": coordinate, "data": {"type": node_type}}

    if node_type == "NODE":
        return node

    if node_type == "CP":
        node["data"]["weight"] = float(line_list[0])  # type: ignore [index]
        return node

    if node_type == "FNODE":
        while line_list:
            key = line_list.pop(0)
            if key.startswith("FIBER"):
                node["data"][key] = _extract_vector(line_list, entry_type=float, size=3)  # type: ignore
                continue
            node["data"][key] = _FNODE_CASTING[key](line_list)  # type: ignore [index]
        return node

    raise ValueError(f"Unknown node type {node_type}")


def write_node(node: dict) -> str:
    """Write node as line.

    Args:
        node: Node as dict

    Returns:
        Node as line
    """
    node_type = node["data"]["type"]
    line = f"{node_type} {node['id']} COORD {to_dat_string(node['COORD'])}"

    if node_type == "NODE":
        return line

    if node_type == "CP":
        return line + " " + str(node["data"]["weight"])

    if node_type == "FNODE":
        for k, v in node["data"].items():
            if k == "type":
                continue
            line += f" {k} {to_dat_string(v)}"
        return line

    raise ValueError(f"Unknown node type {node_type}")
