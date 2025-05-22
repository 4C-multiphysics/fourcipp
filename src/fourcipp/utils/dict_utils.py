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
"""Dict utils."""

from typing import Any, Callable, Iterator, Optional, TypeAlias

import numpy as np
from loguru import logger

Keys: TypeAlias = list | tuple


def compare_nested_dicts_or_lists(
    obj: Any,
    reference_obj: Any,
    allow_int_vs_float_comparison: bool = False,
    rtol: float = 1.0e-5,
    atol: float = 1.0e-8,
    equal_nan: bool = False,
    custom_compare: Optional[Callable] = None,
) -> bool:
    """Recursively compare two nested dictionaries or lists.

    In case objects are not within the provided tolerance an `AssertionError` is raised.

    To compare custom python objects, a `custom_compare` callable can be provided which:
        - Returns nothing/`None` if the objects where not compared within `custom_compare`
        - Returns `True` if the objects are seen as equal
        - Raises AssertionError if the objects are not equal

    Args:
        obj: Object for comparison
        reference_obj: Reference object
        allow_int_vs_float_comparison: Allow a tolerance based comparison between int and
                                              float
        rtol: The relative tolerance parameter for numpy.isclose
        atol: The absolute tolerance parameter for numpy.isclose
        equal_nan: Whether to compare NaN's as equal for numpy.isclose
        custom_compare: Callable to compare objects within this nested framework

    Returns:
        True if the dictionaries are equal
    """
    # Compare non-standard python objects
    if custom_compare is not None:
        # Check if result is not None
        if result := custom_compare(obj, reference_obj) is not None:
            return result

    # Ensures the types are the same
    if not type(obj) is type(reference_obj):
        if (
            not allow_int_vs_float_comparison  # Except floats can be ints
            or not isinstance(obj, (float, int))
            or not isinstance(reference_obj, (float, int))
        ):
            raise AssertionError(
                f"Object is of type {type(obj)}, but the reference is of type {type(reference_obj)}"
            )

    # Objects are numerics
    if isinstance(obj, (float, int)):
        if not np.isclose(obj, reference_obj, rtol, atol, equal_nan):
            raise AssertionError(
                f"The numerics are not close:\n\nobj = {obj}\n\nreference_obj = {reference_obj}"
            )
        return True

    # Object are dicts
    if isinstance(obj, dict):
        # ^ is the symmetric difference operator, i.e. union of the sets without the intersection
        if missing_keys := set(obj.keys()) ^ set(reference_obj.keys()):
            raise AssertionError(
                f"The following keys could not be found in both dicts {missing_keys}:"
                f"\nobj: {obj}\n\nreference_obj:{reference_obj}"
            )
        for key in obj:
            compare_nested_dicts_or_lists(
                obj[key],
                reference_obj[key],
                allow_int_vs_float_comparison,
                rtol,
                atol,
                equal_nan,
                custom_compare,
            )
        return True

    # Objects are lists
    if isinstance(obj, list):
        if len(obj) != len(reference_obj):
            raise AssertionError(
                f"The list lengths differ (got {len(obj)} and {len(reference_obj)}).\nobj "
                f"{obj}\n\nreference_obj:{reference_obj}"
            )
        for obj_item, reference_obj_item in zip(obj, reference_obj):
            compare_nested_dicts_or_lists(
                obj_item,
                reference_obj_item,
                allow_int_vs_float_comparison,
                rtol,
                atol,
                equal_nan,
                custom_compare,
            )
        return True

    # Otherwise compare the objects directly
    if obj != reference_obj:
        raise AssertionError(
            f"The objects are not equal:\n\nobj = {obj}\n\nreference_obj = {reference_obj}"
        )

    return True


def _get_dict(
    nested_dict: dict | list, keys: Keys, optional: bool = True
) -> Iterator[dict]:
    """Return dict entry within a nested dict by keys.

    In case a list is encountered, this function yields over every entry.

    Args:
        nested_dict: dict to iterate. Due to recursiveness, this can also be a list
        keys: List of keys to access
        optional: If the entry is part of a collection that does no exist as it is optional

    Yields:
        Desired data
    """
    # Start with the original data
    sub_data = nested_dict
    sub_keys = list(keys)

    # Get from dict
    if isinstance(nested_dict, dict):
        # Loop over all keys
        for key in keys:
            # Jump into the dict
            if isinstance(sub_data, dict):
                if key in sub_data:
                    # Jump into the entry key
                    sub_data = sub_data[key]
                    sub_keys.pop(0)
                else:
                    # Unknown key
                    if optional:
                        logger.debug(f"Entry {keys} not found and is set as optional")
                        return
                    else:
                        raise KeyError(
                            f"Key '{key}' not found in dictionary {sub_data}."
                        )
            else:
                # Jump into the sub_data with the remaining keys
                yield from _get_dict(sub_data, sub_keys)

                # Exit function afterwards
                return

    # Check the last entry type
    # dict: nothing to do
    if isinstance(sub_data, dict):
        yield sub_data
    # List: jump in an do it all over
    elif isinstance(sub_data, list):
        # Last key is a list of objects
        if not sub_keys:
            for item in sub_data:
                # Only dicts are allowed
                if isinstance(item, dict):
                    yield item
                else:
                    raise TypeError(f"Expected type dict, got {type(item)}")
        # More nested keys
        else:
            for item in sub_data:
                yield from _get_dict(item, sub_keys)
    # Unsupported type
    else:
        raise TypeError(
            f"The current data {sub_data} for type {type(sub_data)} for keys {keys} is neither a dict nor a list."
        )

    # Exit function afterwards
    return


def _split_off_last_key(
    nested_dict: dict,
    keys: Keys,
    optional: bool = True,
    yield_dict_if_missing: bool = False,
) -> Iterator[Any]:
    """Utility to return the last key and its parent entry.

    Args:
        nested_dict: dict to iterate. Due to recursiveness, this can also be a list
        keys: List of keys to access
        optional: If the entry is part of a collection that does no exist as it is optional
        yield_dict_if_missing: Return parent entry even if the entry is not provided

    Yields:
        Parent entry
    """
    last_key = keys[-1]

    for entry in _get_dict(nested_dict, keys[:-1], optional):
        # Key has to be provided
        if last_key not in entry:
            if optional:
                logger.debug(f"Entry {keys} not found and was set to optional.")
                # Still return the dict
                if yield_dict_if_missing:
                    yield entry, last_key
                # Ignore
                else:
                    continue
            else:
                raise KeyError(f"Entry {last_key} not in {entry}")

        yield entry, last_key


def get_entry(
    nested_dict: dict,
    keys: Keys,
    optional: bool = True,
) -> Iterator[Any]:
    """Get entry by a list of keys.

    Args:
        nested_dict: Nested data dict
        keys: List of keys to get the entry
        optional: If the entry is part of a collection that does no exist as it is optional

    Yields:
        Entry
    """
    for entry, last_key in _split_off_last_key(nested_dict, keys, optional):
        yield entry[last_key]


def remove(
    nested_dict: dict,
    keys: Keys,
):
    """Remove entry.

    Args:
        nested_dict: Nested data dict
        keys: List of keys to the entry
        optional: If the entry is part of a collection that does no exist as it is optional
    """
    for entry, last_key in _split_off_last_key(nested_dict, keys):
        entry.pop(last_key)


def replace_value(
    nested_dict: dict,
    keys: Keys,
    new_value: Any,
):
    """Replace value.

    Args:
        nested_dict: Nested data dict
        keys: List of keys to the entry
        new_value: New value to set
    """
    for entry, last_key in _split_off_last_key(nested_dict, keys):
        logger.debug(f"Replacing {last_key}: from {entry[last_key]} to {new_value}")
        entry[last_key] = new_value


def make_default_explicit(
    nested_dict: dict,
    keys: Keys,
    default_value: Any,
):
    """Make default explicit, i.e. set the value in the input.

    Args:
        nested_dict: Nested data dict
        keys: List of keys to the entry
        default_value: Default value to set
    """
    for entry, last_key in _split_off_last_key(
        nested_dict, keys, yield_dict_if_missing=True
    ):
        if last_key not in entry:
            entry[last_key] = default_value


def make_default_implicit(
    nested_dict: dict,
    keys: Keys,
    default_value: Any,
):
    """Make default implicit, i.e., removed it if set with the default value in
    the input.

    Args:
        nested_dict: Nested data dict
        keys: List of keys to the entry
        default_value: Default value to set
    """

    for entry, last_key in _split_off_last_key(nested_dict, keys):
        if entry[last_key] == default_value:
            entry.pop(last_key)


def change_default(
    nested_dict: dict,
    keys: Keys,
    old_default: Any,
    new_default: Any,
):
    """Change default value.

    If default value is not provided the old default is set. Entries where the value equals the new default value is removed.

    Args:
        nested_dict: Nested data dict
        keys: List of keys to the entry
        old_default: Old default value to set
        new_default: New default value
    """
    for entry, last_key in _split_off_last_key(
        nested_dict, keys, yield_dict_if_missing=True
    ):
        # Optional entry is missing
        if last_key not in entry:
            entry[last_key] = old_default
        # If entry is set with the new default, remove it
        else:
            if entry[last_key] == new_default:
                entry.pop(last_key)


def rename_parameter(
    nested_dict: dict,
    keys: Keys,
    new_name: str,
):
    """Rename parameter.

    Args:
        nested_dict: Nested data dict
        keys: List of keys to the entry
        new_name: New name of the parameter
    """

    for entry, last_key in _split_off_last_key(nested_dict, keys):
        entry[new_name] = entry.pop(last_key)
