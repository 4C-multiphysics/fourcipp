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
"""Knotvectors io."""

from functools import partial

from fourcipp.legacy_io.inline_dat import _extract_entry, _extract_enum, _extract_vector

NURBS_PATCH_CASTING = {
    "ID": partial(_extract_entry, entry_type=int),
}

KNOT_VECTORS_CASTING = {
    "NUMKNOTS": partial(_extract_entry, entry_type=int),
    "DEGREE": partial(_extract_entry, entry_type=int),
    "TYPE": partial(_extract_enum, choices=["Interpolated", "Periodic"]),
}


def read_knotvectors(list_of_lines):
    """Read knotvectors section.

    Args:
        list_of_lines (list): List of section lines

    Returns:
        list: List of patch dicts
    """

    patch_dimension = None
    patch_data = {}
    knots_data = {}
    patches = []

    while list_of_lines:
        line = list_of_lines.pop(0)

        # Empty line
        if not line.strip():
            continue

        line_list = line.split()

        # Key value case
        if len(line_list) == 2:
            key = line_list.pop(0)

            # Begin reading in patch
            if key == "NURBS_DIMENSION":
                patch_dimension = partial(_extract_entry, entry_type=int)(line_list)

            elif key == "BEGIN":
                patch_data["knot_vectors"] = []

            # End reading in patch
            elif key == "END":
                # Check dimension
                if (nurbs_dimension := len(patch_data["knot_vectors"])) != (
                    nurbs_dimension_expected := patch_dimension
                ):
                    raise ValueError(
                        f"Expected {nurbs_dimension_expected} knot vectors, got {nurbs_dimension}"
                    )

                # Add patch
                patches.append(patch_data.copy())

                # Reset patch data
                patch_data = {}
            elif key in NURBS_PATCH_CASTING:
                # Add patch data
                patch_data[key] = NURBS_PATCH_CASTING[key](line_list)
            elif key in KNOT_VECTORS_CASTING:
                # Add knot data
                knots_data[key] = KNOT_VECTORS_CASTING[key](line_list)
            else:
                raise ValueError(f"Could not read line: {line}")

        # Values only
        elif len(line_list) == 1:
            # Read knots, the first entry is line_list
            knots_data["knots"] = [
                float(line_list[0])
            ] + _extract_vector(  # misuse this function to extract from list of lines
                list_of_lines, entry_type=float, size=knots_data.pop("NUMKNOTS") - 1
            )

            # Append knots data
            patch_data["knot_vectors"].append(knots_data.copy())

            # Reset knots data
            knots_data = {}

        else:
            raise ValueError(f"Could not read line: {line}")

    return patches


def write_knotvectors(patches):
    """Read knotvectors sections.

    Args:
        patches (dict): Patches list

    Returns:
        list: List of lines
    """

    def write_patch(patch):
        """Write patch lines.

        Args:
            patch (dict): Patch dict

        Returns:
            list: List of lines
        """

        # Patch data
        patch_lines = [
            f"NURBS_DIMENSION {len(patch['knot_vectors'])}",
            "BEGIN NURBSPATCH",
            f"ID {patch['ID']}",
        ]

        # Add knot vectors
        for knot_vector in patch["knot_vectors"]:
            patch_lines.append(f"NUMKNOTS {len(knot_vector['knots'])}")
            patch_lines.append(f"DEGREE {knot_vector['DEGREE']}")
            patch_lines.append(f"TYPE {knot_vector['TYPE']}")
            patch_lines.extend(knot_vector["knots"])

        # End key
        patch_lines.append("END NURBSPATCH")
        return patch_lines

    lines = []
    for patch in patches:
        lines.extend(write_patch(patch))

    return lines
