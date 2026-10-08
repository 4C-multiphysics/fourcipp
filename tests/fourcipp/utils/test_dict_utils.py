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

import numpy as np
import pytest

from fourcipp.utils.dict_utils import (
    _get_dict,
    change_default,
    compare_nested_dicts_or_lists,
    get_entry,
    make_default_explicit,
    make_default_implicit,
    remove,
    rename_parameter,
    replace_value,
    sort_alphabetically,
    sort_by_key_order,
    transform_value,
)


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


def custom_compare(obj, reference_obj):
    """Examplary custom comparison function.

    Args:
        obj (object): Object for comparison
        reference_obj (object): Reference object

    Returns:
        bool: True if objects are equal
    """
    # Handle np.ndarray
    if isinstance(obj, np.ndarray) and isinstance(reference_obj, np.ndarray):
        if not np.array_equal(obj, reference_obj):
            raise AssertionError("Custom compare")
        return True

    # Nothing to return if objects are not compared here


def test_compare_with_custom_function():
    """Test comparison with custom compare."""
    obj = {"b": [{"a": np.ones(2)}], "c": {"a": 1}}
    reference_obj = {"b": [{"a": np.ones(2)}], "c": {"a": 1}}

    assert compare_nested_dicts_or_lists(
        obj, reference_obj, custom_compare=custom_compare
    )


def test_compare_with_custom_function_failure():
    """Test comparison failure with custom compare."""
    obj = {"b": [{"a": np.ones(2)}], "c": {"a": 1}}
    reference_obj = {"b": [{"a": 2 * np.ones(2)}], "c": {"a": 1}}

    with pytest.raises(AssertionError, match="Custom compare"):
        compare_nested_dicts_or_lists(obj, reference_obj, custom_compare=custom_compare)


@pytest.fixture(name="nested_input_dict")
def fixture_nested_input_dict():
    """Nested dict feature."""
    nested_input_dict = {
        "a": {
            "b": [
                {
                    "c": 1,
                    "d": {"e": {"g": [5, 1]}, "h": [{"a": 5}, {"b": 5}], "f": 2},
                    "i": 4,
                },
                {
                    "c": 2,
                    "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                    "i": 5,
                },
                {"c": 1, "d": {"e": {"g": [7, 3]}, "h": [{"a": 7}, {"b": 1}], "f": 2}},
            ],
            "f": 3,
        }
    }
    return nested_input_dict


@pytest.mark.parametrize(
    "keys,value",
    [
        (
            ("a"),
            [
                {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": 5}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                            "i": 5,
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": 1}],
                                "f": 2,
                            },
                        },
                    ],
                    "f": 3,
                }
            ],
        ),
        (
            ("a", "b"),
            [
                [
                    {
                        "c": 1,
                        "d": {"e": {"g": [5, 1]}, "h": [{"a": 5}, {"b": 5}], "f": 2},
                        "i": 4,
                    },
                    {
                        "c": 2,
                        "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                        "i": 5,
                    },
                    {
                        "c": 1,
                        "d": {"e": {"g": [7, 3]}, "h": [{"a": 7}, {"b": 1}], "f": 2},
                    },
                ]
            ],
        ),
        (("a", "b", "c"), [1, 2, 1]),
        (("a", "b", "d", "h", "b"), [5, 1]),
    ],
)
def test_get_entry(nested_input_dict, keys, value):
    """Test get entry."""
    data = get_entry(nested_input_dict, keys)
    for i, entry in enumerate(data):
        assert entry == value[i]


@pytest.mark.parametrize(
    "keys",
    [
        ("not existing"),  # first not exists
        ("a", "b", "d", "h", "b"),  # does not exist but not in every entry of the list
        ("a", "not existing"),  # does not exist in the last key
    ],
)
def test_get_entry_not_optional(nested_input_dict, keys):
    """Test get entry without optional setting."""
    with pytest.raises(KeyError):
        for _ in get_entry(nested_input_dict, keys, optional=False):
            pass


@pytest.mark.parametrize(
    "keys, value",
    [
        (("a"), {}),
        (("a", "b"), {"a": {"f": 3}}),
        (
            ("a", "b", "d", "h", "b"),
            {
                "a": {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                            "i": 5,
                        },
                        {
                            "c": 1,
                            "d": {"e": {"g": [7, 3]}, "h": [{"a": 7}, {}], "f": 2},
                        },
                    ],
                    "f": 3,
                }
            },
        ),
    ],
)
def test_remove(nested_input_dict, keys, value):
    """Test remove parameter."""
    remove(nested_input_dict, keys)
    assert nested_input_dict == value


@pytest.mark.parametrize(
    "keys, value",
    [
        (("a"), {"a": "new_value"}),
        (("a", "b"), {"a": {"f": 3, "b": "new_value"}}),
        (
            ("a", "b", "d", "h", "b"),
            {
                "a": {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": "new_value"}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                            "i": 5,
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": "new_value"}],
                                "f": 2,
                            },
                        },
                    ],
                    "f": 3,
                }
            },
        ),
    ],
)
def test_replace_value(nested_input_dict, keys, value):
    """Test replace value."""
    replace_value(nested_input_dict, keys, "new_value")
    assert nested_input_dict == value


@pytest.mark.parametrize(
    "keys, value",
    [
        (
            ("a", "b", "d", "h", "b"),
            {
                "a": {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": 50}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                            "i": 5,
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": 10}],
                                "f": 2,
                            },
                        },
                    ],
                    "f": 3,
                }
            },
        ),
    ],
)
def test_transform_value(nested_input_dict, keys, value):
    """Test transform value."""
    transform_value(nested_input_dict, keys, lambda current: current * 10)
    assert nested_input_dict == value


def test_transform_value_scalar(nested_input_dict):
    """Test transform value for a plain scalar entry."""
    transform_value(nested_input_dict, ("a", "f"), lambda current: current * 10)
    assert nested_input_dict["a"]["f"] == 30


@pytest.mark.parametrize(
    "keys, value",
    [
        (
            ("a", "j"),
            {
                "a": {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": 5}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                            "i": 5,
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": 1}],
                                "f": 2,
                            },
                        },
                    ],
                    "f": 3,
                    "j": "default",
                }
            },
        ),
        (
            ("a", "b", "i"),
            {
                "a": {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": 5}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                            "i": 5,
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": 1}],
                                "f": 2,
                            },
                            "i": "default",
                        },
                    ],
                    "f": 3,
                }
            },
        ),
    ],
)
def test_make_default_explicit(nested_input_dict, keys, value):
    """Test make default explicit."""
    make_default_explicit(nested_input_dict, keys, "default")
    assert nested_input_dict == value


@pytest.mark.parametrize(
    "keys, value, default",
    [
        (
            ("a", "f"),
            {
                "a": {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": 5}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                            "i": 5,
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": 1}],
                                "f": 2,
                            },
                        },
                    ],
                }
            },
            3,
        ),
        (
            ("a", "b", "i"),
            {
                "a": {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": 5}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": 1}],
                                "f": 2,
                            },
                        },
                    ],
                    "f": 3,
                },
            },
            5,
        ),
    ],
)
def test_make_default_implicit(nested_input_dict, keys, value, default):
    """Test make default implicit."""
    make_default_implicit(nested_input_dict, keys, default)
    assert nested_input_dict == value


@pytest.mark.parametrize(
    "keys, value, old_default, new_default",
    [
        (
            ("a", "b", "i"),
            {
                "a": {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": 5}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": 1}],
                                "f": 2,
                            },
                            "i": 3,
                        },
                    ],
                    "f": 3,
                }
            },
            3,
            5,
        )
    ],
)
def test_make_change_default(nested_input_dict, keys, value, old_default, new_default):
    """Test change default."""
    change_default(nested_input_dict, keys, old_default, new_default)
    assert nested_input_dict == value


@pytest.mark.parametrize(
    "keys, value",
    [
        (
            ("a", "b"),
            {
                "a": {
                    "new_name": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": 5}],
                                "f": 2,
                            },
                            "i": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                            "i": 5,
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": 1}],
                                "f": 2,
                            },
                        },
                    ],
                    "f": 3,
                }
            },
        ),
        (
            ("a", "b", "i"),
            {
                "a": {
                    "b": [
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [5, 1]},
                                "h": [{"a": 5}, {"b": 5}],
                                "f": 2,
                            },
                            "new_name": 4,
                        },
                        {
                            "c": 2,
                            "d": {"e": {"g": [6, 2]}, "h": [{"a": 6}], "f": 2},
                            "new_name": 5,
                        },
                        {
                            "c": 1,
                            "d": {
                                "e": {"g": [7, 3]},
                                "h": [{"a": 7}, {"b": 1}],
                                "f": 2,
                            },
                        },
                    ],
                    "f": 3,
                }
            },
        ),
    ],
)
def test_rename_parameter(nested_input_dict, keys, value):
    """Test renaming parameter."""
    rename_parameter(nested_input_dict, keys, "new_name")
    assert nested_input_dict == value


def test_rename_parameter_collision_raises():
    """Test that an existing destination name is never overwritten."""
    nested_dict = {"a": [{"b": 1}, {"b": 2, "new_name": 3}]}
    with pytest.raises(KeyError):
        rename_parameter(nested_dict, ["a", "b"], "new_name")
    # Nothing is renamed, not even the collision-free match.
    assert nested_dict == {"a": [{"b": 1}, {"b": 2, "new_name": 3}]}


@pytest.mark.parametrize("nested_dict", [{"a": "string"}, {"a": ["string"]}])
def test_get_dict_failure(nested_dict):
    """Test _get_dict failure."""
    with pytest.raises(TypeError):
        for _ in _get_dict(nested_dict, ("a")):
            pass


def test_get_dict_optional(nested_input_dict):
    """Test _get_dict one of the keys does not exist."""
    result = "some value"
    for entry in _get_dict(nested_input_dict, ("a", "not_existing", "b")):
        result = entry
    # assert if nothing changed
    assert result == "some value"


def test_sort_by_key_order_basic():
    """Test sorting by key order."""

    data = {"b": 2, "a": 1, "c": 3}

    assert sort_by_key_order(data, ["a", "b", "c"]) == {"a": 1, "b": 2, "c": 3}


def test_sort_by_key_order_error_mismatched_keys():
    """Test sorting by key order with mismatched keys."""

    data = {"b": 2, "a": 1, "c": 3}

    with pytest.raises(
        ValueError, match="'key_order' must include all keys in the dictionary!"
    ):
        sort_by_key_order(data, ["a", "b"])


def test_sort_alphabetically():
    """Test alphabetical sorting."""

    data = {"A": 1, "b": 2, "a": 0, "B": 3, "c": 4, "C": 5}

    assert sort_alphabetically(data) == {"a": 0, "A": 1, "b": 2, "B": 3, "c": 4, "C": 5}
