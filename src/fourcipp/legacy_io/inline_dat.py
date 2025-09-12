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
"""Read inline dat strings."""

from functools import partial
from typing import Any

from fourcipp.utils.metadata import Primitive
from fourcipp.utils.type_hinting import (
    Extractor,
    LineCastingDict,
    LineListExtractor,
    NestedCastingDict,
    T,
)

# Metadata types currently supported
SUPPORTED_METADATA_TYPES = Primitive.PRIMITIVE_TYPES + ["enum", "vector"]


def to_dat_string(object: Any) -> str:
    """Convert object to dat style string.
    Args:
        data: Object to be casted

    Returns:
        Object as dict
    """
    if isinstance(object, list):
        return " ".join([str(d) for d in object])
    elif isinstance(object, bool):
        return str(object).lower()
    return str(object)


def _left_pop(line_list: list[str], n_entries: int) -> list[str]:
    """Pop entries the beginning of a list.

    Args:
        line_list: List to extract the entries
        n_entries: Number of entries starting from the beginning of the list

    Returns:
        Extracted entries
    """
    entries = line_list[:n_entries]
    del line_list[:n_entries]
    return entries


def _extract_entry(line_list: list[str], extractor: Extractor[T]) -> T:
    """Extract a single entry from a line list.

    Args:
        line_list: List to extract the entries
        extractor: Function to cast the string into the desired object

    Returns:
        Casted object
    """
    return extractor(_left_pop(line_list, 1)[0])


def _extract_vector(
    line_list: list[str], extractor: Extractor[T], size: int
) -> list[T]:
    """Extract a vector entry from a line list.

    Args:
        line_list: List to extract the entries
        extractor: Function to cast the string into the desired object
        size: Vector size

    Returns:
        Casted vector object
    """
    return [extractor(e) for e in _left_pop(line_list, size)]


def _extract_enum(line_list: list[str], choices: list[str]) -> str:
    """Extract enum entry from a line list.

    Args:
        line_list: List to extract the entries
        choices: Choices for the enum

    Returns:
        Valid enum entry
    """
    entry = _left_pop(line_list, 1)[0]
    if not entry in choices:
        raise ValueError(f"Unknown entry {entry}, valid choices are {choices}")
    return entry


def _entry_casting_factory(spec: dict) -> LineListExtractor:
    """Create the casting function for a spec.

    Args:
        spec: 4C metadata style object description

    Returns:
        Casting function for the spec
    """
    if spec["type"] in Primitive.PRIMITIVE_TYPES_TO_PYTHON:
        return partial(
            _extract_entry, extractor=Primitive.PRIMITIVE_TYPES_TO_PYTHON[spec["type"]]
        )
    elif spec["type"] == "vector":
        value_type = Primitive.PRIMITIVE_TYPES_TO_PYTHON[spec["value_type"]["type"]]
        return partial(_extract_vector, extractor=value_type, size=spec["size"])
    elif spec["type"] == "enum":
        choices = [s["name"] for s in spec["choices"]]
        return partial(_extract_enum, choices=choices)
    else:
        raise NotImplementedError(f"Entry type {spec['type']} not supported.")


def casting_factory(fourc_metadata: dict) -> LineCastingDict:
    """Create casting object for the specs.

    Args:
        fourc_metadata: 4C metadata style object description

    Returns:
        Casting object for the specs by name
    """
    metadata_type = fourc_metadata["type"]

    if metadata_type == "all_of":
        specs: LineCastingDict = {}

        for spec_i in fourc_metadata["specs"]:
            if spec_i["type"] in SUPPORTED_METADATA_TYPES:
                spec_name: str = spec_i["name"]
                specs[spec_name] = _entry_casting_factory(spec_i)
            else:
                raise NotImplementedError(f"Entry type {spec_i['type']} not supported.")

        return specs

    raise NotImplementedError(f"First entry has to be an all_of")


def nested_casting_factory(fourc_metadata: dict) -> NestedCastingDict:
    """Create nested casting object for the specs.

    Args:
        fourc_metadata: 4C metadata style object description

    Returns:
        Casting object for the specs by name
    """

    if fourc_metadata["type"] in SUPPORTED_METADATA_TYPES:
        type_name: str = fourc_metadata["name"]
        return {type_name: _entry_casting_factory(fourc_metadata)}

    # Supported collections
    if fourc_metadata["type"] in ["all_of", "group", "one_of"]:
        specs: NestedCastingDict = {}
        for spec_i in fourc_metadata["specs"]:
            specs.update(nested_casting_factory(spec_i))

        if fourc_metadata["type"] == "group":
            type_name = fourc_metadata["name"]
            return {type_name: specs}  # type: ignore[dict-item]
        else:
            return specs
    else:
        raise NotImplementedError(f"Entry type {fourc_metadata['type']} not supported.")


def inline_dat_read(line_list: list, keyword_casting: LineCastingDict) -> dict:
    """Read inline dat to dict.

    Note: This function is not able to read nested containers such as groups. This would diminish
    performance and is not needed for the legacy sections.

    Args:
        line_list: List to extract the entries
        keyword_casting: Dict with the casting

    Returns:
        Entry as dict
    """
    entry: dict = {}
    while line_list:
        key = line_list.pop(0)
        # Raises Error if an entry was provided twice
        if key in entry:
            raise KeyError(f"The entry {key} was provided already: {entry}")
        entry[key] = keyword_casting[key](line_list)

    return entry
