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

import numpy as np


def compare_nested_dicts_or_lists(
    obj,
    reference_obj,
    allow_int_vs_float_comparison=False,
    rtol=1.0e-5,
    atol=1.0e-8,
    equal_nan=False,
):
    """Recursively compare two nested dictionaries or lists.

    In case objects are not within the provided tolerance an `AssertionError` is raised.

    Args:
        obj (object): Object for comparison
        reference_obj (object): Reference object
        allow_int_vs_float_comparison (bool): Allow a tolerance based comparison between int and
                                              float
        rtol (float): The relative tolerance parameter for numpy.isclose
        atol (float): The absolute tolerance parameter for numpy.isclose
        equal_nan (bool): Whether to compare NaN's as equal for numpy.isclose

    Returns:
        bool: True if the dictionaries are equal
    """
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
            )
        return True

    # Otherwise compare the objects directly
    if obj != reference_obj:
        raise AssertionError(
            f"The objects are not equal:\n\nobj = {obj}\n\nreference_obj = {reference_obj}"
        )

    return True
