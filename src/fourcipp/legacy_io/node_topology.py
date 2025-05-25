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
"""Node topology io.

Once this section is implemented in 4C using InputSpec, this file can be
simplified.
"""

from fourcipp.legacy_io.inline_dat import (
    _extract_entry,
    _extract_enum,
    to_dat_string,
)


def _read_corner(line_list: list) -> dict:
    """Read corner line.

    Args:
        line_list: List to extract the entry

    Returns:
        corner as dict
    """
    corner = {
        "type": "CORNER",
        "discretization_type": line_list.pop(0),
        "corner_description": [
            _extract_enum(line_list, choices=["x-", "x+", "y-", "y+", "z-", "z+"]),
            _extract_enum(line_list, choices=["x-", "x+", "y-", "y+", "z-", "z+"]),
            _extract_enum(line_list, choices=["x-", "x+", "y-", "y+", "z-", "z+"]),
        ],
        "d_type": line_list.pop(0),
        "d_id": _extract_entry(line_list, entry_type=int),
    }
    return corner


def _read_edge(line_list: list[str]) -> dict:
    """Read edge line.

    Args:
        line_list: List to extract the entry

    Returns:
        edge as dict
    """
    edge = {
        "type": "EDGE",
        "discretization_type": line_list.pop(0),
        "edge_description": [
            _extract_enum(line_list, choices=["x-", "x+", "y-", "y+", "z-", "z+"]),
            _extract_enum(line_list, choices=["x-", "x+", "y-", "y+", "z-", "z+"]),
        ],
        "d_type": line_list.pop(0),
        "d_id": _extract_entry(line_list, entry_type=int),
    }
    return edge


def _read_side(line_list: list[str]) -> dict:
    """Read side line.

    Args:
        line_list: List to extract the entry

    Returns:
        Side as dict
    """
    side = {
        "type": "SIDE",
        "discretization_type": line_list.pop(0),
        "side_description": [
            _extract_enum(line_list, choices=["x-", "x+", "y-", "y+", "z-", "z+"]),
        ],
        "d_type": line_list.pop(0),
        "d_id": _extract_entry(line_list, entry_type=int),
    }
    return side


def _read_volume(line_list: list[str]) -> dict:
    """Read volume line.

    Args:
        line_list: List to extract the entry

    Returns:
        Volume as dict
    """
    volume = {
        "type": "VOLUME",
        "discretization_type": line_list.pop(0),
        "d_type": line_list.pop(0),
        "d_id": _extract_entry(line_list, entry_type=int),
    }
    return volume


def _read_domain_topology(line_list: list[str], entry_type: str) -> dict:
    """
    Args:
        line_list: List to extract the entry
        entry_type: Type of domain node topology

    Returns:
        Topology entry as a dict
    """
    if entry_type == "CORNER":
        return _read_corner(line_list)
    elif entry_type == "EDGE":
        return _read_edge(line_list)
    elif entry_type == "SIDE":
        return _read_side(line_list)
    elif entry_type == "VOLUME":
        return _read_volume(line_list)
    else:
        raise TypeError(f"Unknown entry type {entry_type}")


def _read_d_topology(line_list: list[str]) -> dict:
    """
    Args:
        line_list: List to extract the entries

    Returns:
        Topology entry as a dict
    """
    node_id = _extract_entry(line_list, entry_type=int)
    d_type = _extract_enum(
        line_list, choices=["DNODE", "DLINE", "DSURFACE", "DSURF", "DVOLUME", "DVOL"]
    )
    d_id = _extract_entry(line_list, entry_type=int)

    d_topology = {
        "type": "NODE",
        "node_id": node_id,
        "d_type": d_type,
        "d_id": d_id,
    }
    return d_topology


def read_node_topology(line: str) -> dict:
    """Read topology entry as line.

    Args:
        line: Inline dat description of the topology entry

    Returns:
        Topology entry as a dict
    """
    line_list = line.split()
    entry_type = line_list.pop(0)

    if entry_type == "NODE":
        return _read_d_topology(line_list)

    if entry_type in ["CORNER", "EDGE", "SIDE", "VOLUME"]:
        return _read_domain_topology(line_list, entry_type)

    raise ValueError(f"Unknown type {entry_type}")


def write_node_topology(topology: dict) -> str:
    """Write topology line.

    Args:
        topology: Topology dict

    Returns:
        Topology entry as line
    """
    return " ".join([to_dat_string(e) for e in topology.values()])
