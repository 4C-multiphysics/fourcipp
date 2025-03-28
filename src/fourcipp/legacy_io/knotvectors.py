from functools import partial

from fourcipp.legacy_io.inline_dat import (
    _extract_entry,
    _extract_vector,
    _extract_enum,
    inline_dat_read,
    to_dat_string,
)

NURBS_PATCH_CASTING = {
    "ID": partial(_extract_entry, entry_type=int),
}

KNOT_VECTORS_CASTING = {
    "NUMKNOTS": partial(_extract_entry, entry_type=int),
    "DEGREE": partial(_extract_entry, entry_type=int),
    "TYPE": partial(_extract_enum, choices=["Interpolated", "Periodic"]),
}


def read_knotvectors(list_of_lines):

    patches = []
    patch_data = {"knot_vectors": []}
    knots_vector = []
    knots_data = {}
    data = {}
    data_vector = []
    current_dimension = None
    max_line_index = len(list_of_lines) - 1
    for i, line in enumerate(list_of_lines):
        if not line.strip():
            continue
        line_list = line.split()
        if len(line_list) == 2:
            key = line_list.pop(0)
            if key == "NURBS_DIMENSION":
                current_dimension = _extract_entry(line_list, entry_type=int)
            elif key == "BEGIN":
                if not current_dimension:
                    raise ValueError("Dimension missing")
                patch_data = {"knot_vectors": []}
                patch_data["NURBS_DIMENSION"] = current_dimension
                print(patch_data)
                knots_data = {"knots": []}
            elif key == "END":
                patches.append(patch_data.copy())
                # patch_data["knot_vectors"].append(knots_data.copy())

                # In a list?
                data_vector.append(patch_data.copy())

                # In a dict?
                data[patch_data.pop("ID")] = patch_data.copy()
            elif key in NURBS_PATCH_CASTING:
                patch_data[key] = NURBS_PATCH_CASTING[key](line_list)
            elif key in KNOT_VECTORS_CASTING:
                knots_data[key] = KNOT_VECTORS_CASTING[key](line_list)
            else:
                raise ValueError(f"Unknown enty: {line}")

        elif len(line_list) == 1:
            knots_vector.append(float(line_list[0]))

            if i == max_line_index or len(list_of_lines[i + 1].split()) == 2:
                if len(knots_vector) != knots_data["NUMKNOTS"]:
                    raise ValueError(
                        f"Expected {knots_data['NUMKNOTS']} but got {len(knots_vector)}"
                    )
                knots_data["knots"] = knots_vector.copy()
                patch_data["knot_vectors"].append(knots_data.copy())
                knots_vector = []

        else:
            raise ValueError(f"Could not read line: {line}")

    # max IDs number of patches?
    # if len(data) != max(data.keys()):
    #    raise ValueError(
    #        f"Number of entries {len(data)} do not match the maximum ID {max(data.keys())}."
    #    )
    return data, data_vector


line = """
NURBS_DIMENSION                       2
BEGIN                           NURBSPATCH
ID                              1
NUMKNOTS                        15
DEGREE                          2
TYPE                            Interpolated
0
0
0
0.1
0.2
0.3
0.4
0.5
0.6
0.7
0.8
0.9
1
1
1
NUMKNOTS                        5
DEGREE                          2
TYPE                            Periodic
0
0
0
0.1
0.2
END NURBSPATCH
NURBS_DIMENSION                       2
BEGIN                           NURBSPATCH
ID                              2
NUMKNOTS                        5
DEGREE                          2
TYPE                            Periodic
0
0
0
0.1
0.3
END NURBSPATCH"""
# from pathlib import Path
# line=Path("/home/ccxi/Downloads/test_nurbs_torus_surface.dat").read_text()
data, data_vector = read_knotvectors(line.split("\n"))
breakpoint()
