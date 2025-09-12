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
"""Test metadata utils."""

import copy

import pytest

from fourcipp import CONFIG
from fourcipp.utils.metadata import (
    All_Of,
    AllEmementsValidator,
    Enum,
    Group,
    List,
    Map,
    One_Of,
    PatternValidator,
    Primitive,
    RangeValidator,
    Selection,
    Tuple,
    Vector,
)
from fourcipp.utils.not_set import check_if_set


@pytest.mark.parametrize("primitive_type", Primitive.PRIMITIVE_TYPES)
def test_primitive(primitive_type):
    """Assert if primitives are set correctly."""
    primitive = Primitive(spec_type=primitive_type, name="primitive_" + primitive_type)
    assert primitive.spec_type == primitive_type
    assert primitive.name == "primitive_" + primitive_type
    assert not check_if_set(primitive.default)
    assert not check_if_set(primitive.description)
    assert primitive.validator is None
    assert primitive.required
    assert not primitive.noneable


@pytest.mark.parametrize("primitive_type", Primitive.PRIMITIVE_TYPES)
def test_primitive_from_4C_metadata(primitive_type):
    """Test primitives from metadata."""
    metadata_dict = {
        "type": primitive_type,
        "name": "primitive_" + primitive_type,
        "description": "this is the description",
        "required": False,
    }
    primitive = Primitive.from_4C_metadata(metadata_dict)
    assert primitive.spec_type == primitive_type
    assert primitive.name == "primitive_" + primitive_type
    assert primitive.description == "this is the description"
    assert not check_if_set(primitive.default)
    assert primitive.validator is None
    assert not primitive.required
    assert not primitive.noneable


def test_primitive_invalid_type():
    """Test if invalid type can be set."""
    with pytest.raises(TypeError, match="Spec type this_is_not_valid"):
        Primitive(spec_type="this_is_not_valid")


@pytest.mark.skip(reason="Some more work needed")
@pytest.mark.parametrize("primitive_type", Primitive.PRIMITIVE_TYPES)
def test_primitive_invalid_default_type(primitive_type):
    """Test if invalid default type."""
    invalid_default = "invalid_default"
    if primitive_type in ["string", "path"]:
        invalid_default = 42
    with pytest.raises(TypeError, match="Default"):
        Primitive(spec_type=primitive_type, default=invalid_default)


def test_enum():
    """Test enum."""
    choices = ["choice_1", "choice_2", "choice_3"]
    enum = Enum(name="enum_name", choices=choices)
    assert enum.name == "enum_name"
    assert enum.choices == choices
    assert not check_if_set(enum.default)
    assert not check_if_set(enum.description)
    assert enum.validator is None
    assert enum.required
    assert not enum.noneable


def test_enum_from_4C_metadata():
    """Test enum from dict."""
    metadata_dict = {
        "name": "enum_name",
        "type": "enum",
        "description": "enum description.",
        "required": False,
        "default": "choice_1",
        "choices": [{"name": "choice_1"}, {"name": "choice_2"}, {"name": "choice_3"}],
    }
    enum = Enum.from_4C_metadata(metadata_dict)
    assert enum.name == "enum_name"
    assert enum.choices == ["choice_1", "choice_2", "choice_3"]
    assert enum.default == "choice_1"
    assert enum.description == "enum description."
    assert enum.validator is None
    assert not enum.required
    assert not enum.noneable


def test_enum_invalid_default_choice():
    """Test invalid default choice."""
    choices = ["choice_1", "choice_2", "choice_3"]
    with pytest.raises(
        ValueError,
        match="Default choice invalid_choice is not in the valid enum choices",
    ):
        Enum(name="enum_name", choices=choices, default="invalid_choice")


@pytest.mark.parametrize("metadata_class", (Vector, Map))
@pytest.mark.parametrize("primitive_type", Primitive.PRIMITIVE_TYPES)
def test_vector_and_maps_primitives(metadata_class, primitive_type):
    """Test vector and map from primitives."""
    metadata_object = metadata_class(Primitive(primitive_type))
    assert isinstance(metadata_object.value_type, Primitive)
    assert not check_if_set(metadata_object.default)
    assert not check_if_set(metadata_object.description)
    assert metadata_object.validator is None
    assert metadata_object.required
    assert not metadata_object.noneable


@pytest.mark.parametrize(
    "metadata_type,metadata_class", (("vector", Vector), ("map", Map))
)
def test_vector_and_maps_from_4C_metadata(metadata_type, metadata_class):
    """Test vector and map from 4C metadata."""
    metadata_dict = {
        "name": metadata_type + "_parameter",
        "type": metadata_type,
        "size": 3,
        "value_type": {"type": "double"},
        "required": True,
    }

    metadata_object = metadata_class.from_4C_metadata(metadata_dict)

    assert isinstance(metadata_object, metadata_class)
    assert isinstance(metadata_object.value_type, Primitive)
    assert metadata_object.name == metadata_type + "_parameter"
    assert not check_if_set(metadata_object.default)
    assert not check_if_set(metadata_object.description)
    assert metadata_object.validator is None
    assert metadata_object.required
    assert not metadata_object.noneable


@pytest.mark.parametrize("metadata_class", (Vector, Map))
def test_vector_and_maps_enum(metadata_class):
    """Test vector and map from enum."""
    metadata_object = metadata_class(Enum(choices=["a", "b"]), size=3)
    assert isinstance(metadata_object.value_type, Enum)
    assert not check_if_set(metadata_object.default)
    assert not check_if_set(metadata_object.description)
    assert metadata_object.validator is None
    assert metadata_object.required
    assert not metadata_object.noneable
    assert metadata_object.size == 3


@pytest.mark.parametrize("metadata_class", (Vector, Map))
def test_nested_vector(metadata_class):
    """Test nested vector and map."""
    metadata_object = metadata_class(
        metadata_class(metadata_class(Primitive("bool")), description="second inner")
    )
    assert isinstance(metadata_object.value_type.value_type.value_type, Primitive)
    assert metadata_object.value_type.description == "second inner"
    assert not check_if_set(metadata_object.default)
    assert not check_if_set(metadata_object.description)
    assert metadata_object.validator is None
    assert metadata_object.required
    assert not metadata_object.noneable


@pytest.mark.parametrize("metadata_class", (Vector, Map))
def test_invalid_value_type_vector(metadata_class):
    """Test invalid value type in vector and maps."""
    with pytest.raises(TypeError, match="Value type invalid_object has to be of type"):
        metadata_class(metadata_class("invalid_object"))


def test_tuple():
    """Test tuple."""
    tuple_object = Tuple((Enum(["choice_1", "choice_2"]), Primitive("int")), size=2)
    assert isinstance(tuple_object.value_types[0], Enum)
    assert isinstance(tuple_object.value_types[1], Primitive)
    assert not check_if_set(tuple_object.default)
    assert not check_if_set(tuple_object.description)
    assert tuple_object.validator is None
    assert tuple_object.required
    assert not tuple_object.noneable


def test_tuple_failure_size():
    """Test failure of the tuple initialization."""
    with pytest.raises(ValueError):
        Tuple((Enum(["choice_1", "choice_2"]), Primitive("int")), size=3)


def test_tuple_invalid_value_types():
    """Test invalid value types in tuples."""
    with pytest.raises(TypeError, match="Value type not a valid type"):
        Tuple((Enum(["choice_1", "choice_2"]), "not a valid type"), size=2)


def test_tuple_from_4C_metadata():
    """Test tuple from 4C metadata."""
    metadata_dict = {
        "value_types": [
            {
                "name": "enum_name",
                "type": "enum",
                "description": "enum description.",
                "required": False,
                "default": "choice_1",
                "choices": [
                    {"name": "choice_1"},
                    {"name": "choice_2"},
                    {"name": "choice_3"},
                ],
            },
            {
                "name": "vector_name",
                "type": "vector",
                "size": 3,
                "value_type": {"type": "double"},
                "required": True,
            },
        ],
        "size": 2,
    }
    tuple_object = Tuple.from_4C_metadata(metadata_dict)
    assert isinstance(tuple_object.value_types[0], Enum)
    assert isinstance(tuple_object.value_types[1], Vector)
    assert not check_if_set(tuple_object.default)
    assert not check_if_set(tuple_object.description)
    assert tuple_object.validator is None
    assert tuple_object.required
    assert not tuple_object.noneable


def test_all_of_from_simple_types():
    """Test All_of from simple types."""
    all_of = All_Of(specs=[Enum(["choice_1", "choice_2"]), Primitive("int")])
    assert isinstance(all_of.specs[0], Enum)
    assert isinstance(all_of.specs[1], Primitive)
    assert not check_if_set(all_of.description)


def test_nested_all_of():
    """Test All_of from simple types and All_of."""
    all_of = All_Of(
        specs=[
            All_Of(
                specs=[
                    Enum(["choice_1", "choice_2"]),
                    Primitive("int", "a"),
                    All_Of(
                        specs=[
                            All_Of(
                                specs=[Primitive("double", "b")],
                            )
                        ]
                    ),
                ]
            ),
            All_Of(specs=[Primitive("bool", "c")]),
        ]
    )
    assert isinstance(all_of.specs[0], Enum)
    assert all_of.specs[1].name == "a"
    assert all_of.specs[2].name == "b"
    assert all_of.specs[3].name == "c"


def test_nested_all_of_with_one_of():
    """Test All_of from simple types, All_of and One_of."""
    all_of = All_Of(
        specs=[
            All_Of(
                specs=[
                    Primitive("int", "a"),
                    All_Of(
                        specs=[
                            All_Of(
                                specs=[
                                    Primitive("double", "b"),
                                    One_Of(
                                        [
                                            Primitive("int", "d"),
                                            Primitive("double", "e"),
                                        ]
                                    ),
                                ],
                            )
                        ]
                    ),
                ]
            ),
            All_Of(specs=[Primitive("bool", "c")]),
        ]
    )

    assert len(all_of) == 1
    assert isinstance(all_of.specs[0], One_Of)
    assert len(all_of.specs[0]) == 2
    assert isinstance(all_of.specs[0].specs[0], All_Of)
    assert isinstance(all_of.specs[0].specs[1], All_Of)
    assert all_of.specs[0].specs[0].specs[0].name == "d"
    assert all_of.specs[0].specs[0].specs[1].name == "b"
    assert all_of.specs[0].specs[0].specs[2].name == "a"
    assert all_of.specs[0].specs[0].specs[3].name == "c"
    assert all_of.specs[0].specs[1].specs[0].name == "e"
    assert all_of.specs[0].specs[1].specs[1].name == "b"
    assert all_of.specs[0].specs[1].specs[2].name == "a"
    assert all_of.specs[0].specs[1].specs[3].name == "c"


def test_add_specs_all_of_from_simple_types():
    """Test add simple input specs."""
    all_of = All_Of(specs=[Enum(["choice_1", "choice_2"]), Primitive("int", "a")])
    all_of.add_specs([Primitive("bool", "b")])

    assert isinstance(all_of.specs[0], Enum)
    assert all_of.specs[1].name == "a"
    assert all_of.specs[2].name == "b"
    assert len(all_of.specs) == 3


def test_add_specs_all_of_nested():
    """Test add nested specs with All_Ofs to All_of."""
    all_of = All_Of(specs=[Enum(["choice_1", "choice_2"]), Primitive("int", "a")])
    all_of.add_specs(
        [
            Primitive("bool", "b"),
            All_Of([Primitive("double", "c"), All_Of([Primitive("int", "d")])]),
        ]
    )

    assert isinstance(all_of.specs[0], Enum)
    assert all_of.specs[1].name == "a"
    assert all_of.specs[2].name == "b"
    assert all_of.specs[3].name == "c"
    assert all_of.specs[4].name == "d"
    assert len(all_of.specs) == 5


def test_all_of_from_4C_metadata():
    """Test All_Of from 4C metadata."""
    metadata_dict = {
        "type": "all_of",
        "specs": [
            {
                "type": "bool",
                "name": "a",
                "description": "this is the description",
                "required": False,
            },
            {
                "type": "all_of",
                "specs": [
                    {
                        "type": "int",
                        "name": "b",
                        "description": "this is the description",
                        "required": False,
                    }
                ],
            },
        ],
    }
    obj = All_Of.from_4C_metadata(metadata_dict)
    assert len(obj) == 2
    assert obj.specs[0].name == "a"
    assert obj.specs[1].name == "b"


def test_one_of_from_4C_metadata():
    """Test one of from 4C metadata."""
    metadata_dict = {
        "type": "one_of",
        "specs": [
            {
                "type": "bool",
                "name": "a",
                "description": "this is the description",
                "required": False,
            },
            {
                "type": "all_of",
                "specs": [
                    {
                        "type": "int",
                        "name": "b",
                        "description": "this is the description",
                        "required": False,
                    }
                ],
            },
        ],
    }
    obj = One_Of.from_4C_metadata(metadata_dict)
    assert len(obj) == 2
    assert len(obj.specs[0]) == 1
    assert len(obj.specs[1]) == 1
    assert obj.specs[0].specs[0].name == "a"
    assert obj.specs[1].specs[0].name == "b"


def test_one_of_from_simple_types():
    """Test one_of from simple types."""
    one_of = One_Of(specs=[Enum(["choice_1", "choice_2"], "a"), Primitive("int", "b")])

    assert not check_if_set(one_of.description)
    assert len(one_of.specs) == 2
    assert isinstance(one_of.specs[0], All_Of)
    assert isinstance(one_of.specs[1], All_Of)
    assert len(one_of.specs[0].specs) == 1
    assert len(one_of.specs[1].specs) == 1
    assert one_of.specs[0].specs[0].name == "a"
    assert one_of.specs[1].specs[0].name == "b"


def test_one_of_from_simple_types_and_all_of():
    """Test one_of from simple types and All_of."""
    one_of = One_Of(
        specs=[
            Enum(["choice_1", "choice_2"], "a"),
            All_Of([Primitive("int", "b"), Primitive("bool", "c")]),
        ]
    )

    assert len(one_of.specs) == 2
    assert isinstance(one_of.specs[0], All_Of)
    assert isinstance(one_of.specs[1], All_Of)
    assert len(one_of.specs[0].specs) == 1
    assert len(one_of.specs[1].specs) == 2
    assert one_of.specs[0].specs[0].name == "a"
    assert one_of.specs[1].specs[0].name == "b"
    assert one_of.specs[1].specs[1].name == "c"


def test_one_of_from_simple_types_and_one_of():
    """Test one_of from simple types and One_ofs."""
    one_of = One_Of(
        specs=[
            Enum(["choice_1", "choice_2"], "a"),
            One_Of([Primitive("int", "b"), All_Of([Primitive("bool", "c")])]),
        ]
    )

    assert len(one_of.specs) == 3
    assert isinstance(one_of.specs[0], All_Of)
    assert isinstance(one_of.specs[1], All_Of)
    assert isinstance(one_of.specs[2], All_Of)
    assert len(one_of.specs[0].specs) == 1
    assert len(one_of.specs[1].specs) == 1
    assert len(one_of.specs[2].specs) == 1
    assert one_of.specs[0].specs[0].name == "a"
    assert one_of.specs[1].specs[0].name == "b"
    assert one_of.specs[2].specs[0].name == "c"


def test_add_specs_one_of():
    """Add specs to One_of."""
    one_of = One_Of(specs=[Enum(["choice_1", "choice_2"], "a"), Primitive("int", "b")])
    one_of.add_specs([Primitive("double", "c"), Primitive("bool", "d")])

    assert len(one_of.specs) == 2
    assert isinstance(one_of.specs[0], All_Of)
    assert isinstance(one_of.specs[1], All_Of)
    assert len(one_of.specs[0].specs) == 3
    assert len(one_of.specs[1].specs) == 3
    assert one_of.specs[0].specs[0].name == "a"
    assert one_of.specs[0].specs[1].name == "c"
    assert one_of.specs[0].specs[2].name == "d"
    assert one_of.specs[1].specs[0].name == "b"
    assert one_of.specs[1].specs[1].name == "c"
    assert one_of.specs[1].specs[2].name == "d"


def test_selection():
    """Test selection."""
    selection = Selection(
        "selection",
        {
            "a": Primitive("double", "a"),
            "b": All_Of([Primitive("int", "b"), Primitive("bool", "c")]),
        },
    )
    assert selection.name == "selection"
    assert len(selection) == 2
    assert isinstance(selection.choices["a"], All_Of)
    assert isinstance(selection.choices["b"], All_Of)
    assert len(selection.choices["a"]) == 1
    assert selection.choices["a"].specs[0].name == "a"
    assert len(selection.choices["b"]) == 2
    assert selection.choices["b"].specs[0].name == "b"
    assert selection.choices["b"].specs[1].name == "c"


def test_selection_from_4C_metadata():
    """Test selection from 4C metadata."""
    metadata_dict = {
        "type": "selection",
        "name": "a_selection",
        "choices": [
            {"name": "choice_a", "spec": {"type": "int", "name": "a"}},
            {
                "name": "choice_b",
                "spec": {"type": "all_of", "specs": [{"type": "double", "name": "b"}]},
            },
        ],
    }
    selection = Selection.from_4C_metadata(metadata_dict)
    assert selection.name == "a_selection"
    assert len(selection) == 2
    assert isinstance(selection.choices["choice_a"], All_Of)
    assert isinstance(selection.choices["choice_b"], All_Of)
    assert len(selection.choices["choice_a"]) == 1
    assert selection.choices["choice_a"].specs[0].name == "a"
    assert len(selection.choices["choice_b"]) == 1
    assert selection.choices["choice_b"].specs[0].name == "b"


@pytest.mark.parametrize("metadata_class", (Group, List))
@pytest.mark.parametrize(
    "spec",
    [
        Primitive("int", "a"),
        All_Of([Primitive("bool", "b"), Primitive("double", "c")]),
    ],
)
def test_group_and_list(metadata_class, spec):
    """Test group and list."""
    metadata = metadata_class(metadata_class.__name__.lower(), spec)
    spec = All_Of([spec])
    assert isinstance(metadata.spec, All_Of)
    for i in range(len(metadata.spec.specs)):
        assert metadata.spec.specs[i].name == spec.specs[i].name


@pytest.mark.parametrize("metadata_class", (Group, List))
@pytest.mark.parametrize(
    "spec",
    (
        {"specs": [{"type": "int", "name": "a"}]},
        {
            "specs": [
                {
                    "type": "all_of",
                    "specs": [{"type": "int", "name": "a"}],
                }
            ]
        },
    ),
)
def test_group_and_list_from_4C_metadata(metadata_class, spec):
    """Test group and list from 4C metadata."""
    spec = copy.deepcopy(spec)
    spec["type"] = metadata_class.__name__.lower()
    spec["name"] = metadata_class.__name__.lower()
    # Difference between group and list
    if metadata_class.__name__ == "List":
        spec["spec"] = spec.pop("specs")[0]
    metadata = metadata_class.from_4C_metadata(spec)
    assert isinstance(metadata.spec, All_Of)
    assert len(metadata.spec) == 1
    assert metadata.spec.specs[0].name == "a"


def test_list_size():
    """Test list size."""
    list_metadata = List("a_list", Primitive("int", "a"), size=5)
    assert list_metadata.size == 5


def test_read_in_metadata_from_config():
    """Sanity check if metadata file can be read in."""
    sections = CONFIG.fourc_metadata["sections"]
    obj = All_Of.from_4C_metadata(sections)
    assert len(obj) > 10


@pytest.mark.parametrize("data_type", (int, float))
@pytest.mark.parametrize(
    "value,minimum_exclusive,maximum_exclusive,expected",
    [
        (2, True, True, True),
        (7, True, True, False),
        (2, False, False, True),
        (7, False, False, False),
        (1, True, True, False),
        (1, False, True, True),
        (5, True, True, False),
        (5, True, False, True),
    ],
)
def test_range_validator(
    data_type, value, minimum_exclusive, maximum_exclusive, expected
):
    """Test range validator."""
    validator = RangeValidator(
        minimum=data_type(1),
        minimum_exclusive=minimum_exclusive,
        maximum=data_type(5),
        maximum_exclusive=maximum_exclusive,
    )
    assert validator(data_type(value)) == expected


@pytest.mark.parametrize("value,expected", [("test this", True), ("abc", False)])
def test_pattern_validator(value, expected):
    """Test pattern validator."""
    validator = PatternValidator("test *")
    assert validator(value) == expected


@pytest.mark.parametrize("value,expected", [([2, 3, 4], True), ([4, 7, 2], False)])
def test_all_elements(value, expected):
    """Test all elements validator."""
    validator = AllEmementsValidator(RangeValidator(1, 4))
    assert validator(value) == expected
