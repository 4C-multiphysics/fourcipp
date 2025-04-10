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
"""Test dict utils."""

import pytest

from fourcipp.utils.dict_utils import compare_nested_dicts_or_lists


@pytest.mark.parametrize(
    "obj,reference_obj",
    [
        ([1, 2, 3], [1, 2, 3]),
        ({"a": 1, "b": 2, "c": 3}, {"c": 3, "b": 2, "a": 1}),
        (
            {
                "a": 1,
                "b": {"g": [{"a": 2, "d": [{"f": 2}, {"e": 2.1}]}], "a": 2},
                "c": [3, True],
            },
            {
                "c": [3, True],
                "b": {"a": 2, "g": [{"a": 2, "d": [{"f": 2}, {"e": 2.1}]}]},
                "a": 1,
            },
        ),
        ("text", "text"),
    ],
)
def test_compare(obj, reference_obj):
    """Test comparison."""
    assert compare_nested_dicts_or_lists(obj, reference_obj)


@pytest.mark.parametrize(
    "obj,reference_obj",
    [
        ([1, 2, 3], [1, 2.1, 3]),
        ({"a": 1, "b": 2, "d": 3}, {"c": 3, "b": 2, "a": 1}),
        (
            {
                "a": 1,
                "b": {"g": [{"a": 2, "d": [{"f": 2}, {"e": 2.1}]}], "a": 2},
                "c": [3.1, True],
            },
            {
                "c": [3, True],
                "b": {"a": 2, "g": [{"a": 2, "d": [{"f": 2}, {"e": 2.1}]}]},
                "a": 1,
            },
        ),
        (True, False),
        (True, "text"),
        ("some", "text"),
        ([1, 2], [1, 2, 3]),
        (True, 1.0),  # Important test since isinstance(True, int) is true
    ],
)
def test_compare_failure(obj, reference_obj):
    """Test comparison failure."""
    with pytest.raises(AssertionError):
        compare_nested_dicts_or_lists(obj, reference_obj)


@pytest.mark.parametrize(
    "obj,reference_obj",
    [
        (0, -0.00000001),
        ([1, 2, 3], [1, 2.0, 3]),
        ({"a": 1, "b": 2, "c": 3}, {"c": 3, "b": 2, "a": 1.000005}),
        (
            {
                "a": 1,
                "b": {"g": [{"a": 2, "d": [{"f": 2.0000005}, {"e": 2.1}]}], "a": 2},
                "c": [3, True],
            },
            {
                "c": [3, True],
                "b": {"a": 2, "g": [{"a": 2, "d": [{"f": 2.0}, {"e": 2.1}]}]},
                "a": 1,
            },
        ),
    ],
)
def test_compare_allow_int_as_float(obj, reference_obj):
    """Test comparison but compare ints to floats."""
    assert compare_nested_dicts_or_lists(
        obj, reference_obj, allow_int_vs_float_comparison=True
    )


@pytest.mark.parametrize(
    "obj,reference_obj",
    [
        (0, -0.001),
        ([1, 2, 3], [1, 2.02, 3]),
        ({"a": 1, "b": 2, "c": 3}, {"c": 3, "b": 2, "a": 1.005}),
        (
            {
                "a": 1,
                "b": {"g": [{"a": 2, "d": [{"f": 2.05}, {"e": 2.1}]}], "a": 2},
                "c": [3, True],
            },
            {
                "c": [3, True],
                "b": {"a": 2, "g": [{"a": 2, "d": [{"f": 2.0}, {"e": 2.1}]}]},
                "a": 1,
            },
        ),
    ],
)
def test_compare_allow_int_as_float_failure(obj, reference_obj):
    """Test comparison failure due to tolerance."""
    with pytest.raises(AssertionError, match="The numerics are not close"):
        compare_nested_dicts_or_lists(
            obj, reference_obj, allow_int_vs_float_comparison=True
        )
