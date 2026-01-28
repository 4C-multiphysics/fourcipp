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
"""Utils for legacy io testing."""

from loguru import logger

from fourcipp.legacy_io.element import to_dat_string

# This map is used to generate elements from the metadata file
_TESTING_MAP = {"int": 4, "double": 2.11, "string": "text", "bool": True}


def iterate_all_of(all_of):
    """Iterate over all_of and one_ofs.

    Args:
        all_of (dict): all_of dictionary

    Yields:
        dict: specs of the all_of
    """
    for spec in all_of["specs"]:
        if spec["type"] == "all_of":
            yield from iterate_all_of(spec)
        elif spec["type"] == "one_of":
            for spec in spec["specs"]:
                yield from iterate_all_of(spec)
        else:
            yield spec
    return


def reference_value_from_all_of(all_of):
    """Generate line from all_of.

    Args:
        all_of (dict): Metadata dict for the group

    Returns:
        str: inline
    """

    keyword_parameters = {}
    positional_parameters = {}

    for parameter in iterate_all_of(all_of):
        entry = None
        if parameter["type"] in _TESTING_MAP:
            entry = _TESTING_MAP[parameter["type"]]
        elif parameter["type"] == "vector":
            entry = [_TESTING_MAP[parameter["value_type"]["type"]]] * parameter["size"]
        elif parameter["type"] == "enum":
            entry = parameter["choices"][0]["name"]
        elif parameter["type"] in ["selection", "group", "list", "all_of", "one_of"]:
            logger.info(
                f"The 4C legacy reader does not support parameters of type {parameter['type']}. Skipping the test for parameter \n{parameter}"
            )
            continue
        else:
            raise ValueError(f"Could not create testing line from {parameter['type']}")

        if parameter["name"].startswith("_positional"):
            _, _, position, _ = parameter["name"].split("_", 3)
            positional_parameters[int(position)] = entry
        else:
            keyword_parameters[parameter["name"]] = to_dat_string(entry)

    line_list = [
        to_dat_string(positional_parameters[e])
        for e in sorted(positional_parameters.keys())
    ]
    for e in keyword_parameters.items():
        line_list.extend(e)
    return "  ".join(line_list)
