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
"""YAML io."""

import json
import pathlib
from typing import Callable

import regex
import ryml

from fourcipp.utils.type_hinting import Path


def load_yaml(path_to_yaml_file: Path) -> dict:
    """Load yaml files.

    rapidyaml is the fastest yaml parsing library we could find. Since it returns custom objects we
    use the library to emit the objects to json and subsequently read it in using the json library.
    This is still two orders of magnitude faster compared to other yaml libraries.

    Args:
        path_to_yaml_file: Path to yaml file

    Returns:
       Loaded data
    """

    json_str = ryml.emit_json(
        ryml.parse_in_arena(pathlib.Path(path_to_yaml_file).read_bytes())
    )

    # Convert `inf` to a string to avoid JSON parsing errors, see https://github.com/biojppm/rapidyaml/issues/312
    json_str = regex.sub(r":\s*(-?)inf\b", r': "\1inf"', json_str)

    # Convert floats that are missing digits on either side of the decimal point
    # so .5 to 0.5 and 5. to 5.0
    json_str = regex.sub(r":\s*(-?)\.([0-9]+)", r": \g<1>0.\2", json_str)
    json_str = regex.sub(r":\s*(-?)([0-9]+)\.(\D)", r": \1\2.0\3", json_str)

    data = json.loads(json_str)

    return data


def dict_to_yaml_string(
    data: dict,
    sort_function: Callable[[dict], dict] | None = None,
    use_fourcipp_yaml_style: bool = True,
) -> str:
    """Dump dict as yaml.

    The FourCIPP yaml style sets flow
    Args:
        data: Data to dump.
        sort_function: Function to sort the data.
        use_fourcipp_yaml_style: If FourCIPP yaml style is to be used

    Returns:
        YAML string representation of the data
    """

    if sort_function is not None:
        data = sort_function(data)

    # Convert dictionary into a ryml tree
    tree = ryml.parse_in_arena(bytearray(json.dumps(data).encode("utf8")))

    def check_is_vector(tree: ryml.Tree, node_id: int) -> bool:
        """Check if sequence is of ints, floats or sequence there of.

        In 4C metadata terms, list of strings, bools, etc. could also be vectors.
        For the sake of simplicity these are omitted.

        Args:
            tree (ryml.Tree): Tree to check
            node_id (int): Node id

        Returns:
            returns if entry is a vector
        """

        for sub_node, _ in ryml.walk(tree, node_id):
            # Ignore the root node
            if sub_node == node_id:
                continue

            # If sequence contains a dict
            if tree.is_map(sub_node):
                return False

            # If sequence contains a sequence
            elif tree.is_seq(sub_node):
                if not check_is_vector(tree, sub_node):
                    return False

            # Else it's a value
            else:
                val = tree.val(sub_node).tobytes().decode("ascii")
                is_not_numeric = (
                    tree.is_val_quoted(sub_node)  # string
                    or tree.val_is_null(sub_node)  # null
                    or val == "true"  # bool
                    or val == "false"  # bool
                )
                if is_not_numeric:
                    return False

        return True

    # Change style bits to avoid JSON output and format vectors correctly
    # see https://github.com/biojppm/rapidyaml/issues/520
    for node_id, depth in ryml.walk(tree):
        if tree.is_map(node_id):
            tree.set_container_style(node_id, ryml.NOTYPE)
        elif tree.is_seq(node_id):
            if (
                not use_fourcipp_yaml_style  # do not do special formatting
                or depth == 1  # is a section
                or not check_is_vector(tree, node_id)  # is not a vector
            ):
                tree.set_container_style(node_id, ryml.NOTYPE)

        if tree.has_key(node_id):
            tree.set_key_style(node_id, ryml.NOTYPE)

    yaml_string = ryml.emit_yaml(tree)

    if use_fourcipp_yaml_style:
        # add spaces after commas in vectors
        yaml_string = regex.sub(r"(?<=\d),(?=\d)|(?<=\]),(?=\[)", ", ", yaml_string)

    return yaml_string


def dump_yaml(
    data: dict,
    path_to_yaml_file: Path,
    sort_function: Callable[[dict], dict] | None = None,
    use_fourcipp_yaml_style: bool = True,
) -> None:
    """Dump yaml to file.

    Args:
        data: Data to dump.
        path_to_yaml_file: Yaml file path
        sort_function: Function to sort the data
        use_fourcipp_yaml_style: If FourCIPP yaml style is to be used
    """
    pathlib.Path(path_to_yaml_file).write_text(
        dict_to_yaml_string(data, sort_function, use_fourcipp_yaml_style),
        encoding="utf-8",
    )
