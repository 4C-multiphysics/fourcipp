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
"""Test migration operation handlers."""

import pytest

from fourcipp.migration.errors import MigrationError
from fourcipp.migration.operations import OPERATIONS


@pytest.fixture(name="sections")
def fixture_sections():
    """Minimal, realistic input file sections dict."""
    return {
        "MATERIALS": [
            {"MAT": 1, "MAT_ElastHyper": {"NUMMAT": 2, "MATIDS": [10, 11]}},
            {"MAT": 2, "MAT_StVenantKirchhoff": {"YOUNG": 1.0, "NUE": 0.3}},
            {"MAT": 3, "MAT_ElastHyper": {"NUMMAT": 1, "MATIDS": [12]}},
        ],
        "STRUCTURAL DYNAMIC": {"DYNAMICTYPE": "Statics"},
    }


def test_operations_registry_covers_all_auto_fix_types():
    """Every documented auto-fix migration type must be registered."""
    assert set(OPERATIONS) == {
        "parameter_removed",
        "parameter_renamed",
        "parameter_default_changed",
        "parameter_added",
        "section_renamed",
        "section_merged",
        "parameter_value_renamed",
        "parameter_moved",
        "type_renamed",
        "section_added",
    }


def test_parameter_removed(sections):
    """Test that a parameter is removed for every matching material."""
    OPERATIONS["parameter_removed"](
        sections, {"path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"]}
    )
    for material in sections["MATERIALS"]:
        if "MAT_ElastHyper" in material:
            assert "NUMMAT" not in material["MAT_ElastHyper"]
    assert sections["MATERIALS"][2]["MAT_ElastHyper"]["MATIDS"] == [12]


def test_parameter_removed_absent_is_noop(sections):
    """Test that removing an already-absent parameter does not raise."""
    OPERATIONS["parameter_removed"](
        sections, {"path": ["MATERIALS", "MAT_ElastHyper", "DOES_NOT_EXIST"]}
    )


def test_parameter_renamed(sections):
    """Test renaming a parameter within a section."""
    OPERATIONS["parameter_renamed"](
        sections,
        {"path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"], "new_name": "DYNAMICTYP"},
    )
    assert sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYP": "Statics"}


def test_parameter_default_changed(sections):
    """Test setting an old default explicitly, and dropping the new default."""
    OPERATIONS["parameter_default_changed"](
        sections,
        {
            "path": ["MATERIALS", "MAT_StVenantKirchhoff", "NUE"],
            "old_default": 0.3,
            "new_default": 0.0,
        },
    )
    # Was already explicitly set, and not equal to the new default: untouched.
    assert sections["MATERIALS"][1]["MAT_StVenantKirchhoff"]["NUE"] == 0.3

    OPERATIONS["parameter_default_changed"](
        sections,
        {
            "path": ["MATERIALS", "MAT_StVenantKirchhoff", "YOUNG"],
            "old_default": 5.0,
            "new_default": 1.0,
        },
    )
    # Was explicitly set to the (old) new_default value, so it is dropped.
    assert "YOUNG" not in sections["MATERIALS"][1]["MAT_StVenantKirchhoff"]


def test_parameter_added_only_if_parent_exists(sections):
    """Test that a parameter is only added where its parent context exists."""
    OPERATIONS["parameter_added"](
        sections, {"path": ["MATERIALS", "MAT_ElastHyper", "DENS"], "value": 0.0}
    )
    assert sections["MATERIALS"][0]["MAT_ElastHyper"]["DENS"] == 0.0
    assert sections["MATERIALS"][2]["MAT_ElastHyper"]["DENS"] == 0.0
    assert "DENS" not in sections["MATERIALS"][1]["MAT_StVenantKirchhoff"]


def test_section_renamed(sections):
    """Test renaming a top-level section."""
    OPERATIONS["section_renamed"](
        sections,
        {"path": ["STRUCTURAL DYNAMIC"], "new_name": "STRUCTURE DYNAMIC"},
    )
    assert "STRUCTURAL DYNAMIC" not in sections
    assert sections["STRUCTURE DYNAMIC"] == {"DYNAMICTYPE": "Statics"}


def test_type_renamed(sections):
    """Test renaming a material type discriminator key."""
    OPERATIONS["type_renamed"](
        sections,
        {"path": ["MATERIALS", "MAT_ElastHyper"], "new_name": "MAT_HyperElast"},
    )
    for material in sections["MATERIALS"]:
        assert "MAT_ElastHyper" not in material
    assert sections["MATERIALS"][0]["MAT_HyperElast"]["NUMMAT"] == 2
    assert sections["MATERIALS"][2]["MAT_HyperElast"]["NUMMAT"] == 1
    # Unrelated material types are untouched.
    assert sections["MATERIALS"][1]["MAT_StVenantKirchhoff"]["YOUNG"] == 1.0


def test_section_added_new_section(sections):
    """Test that a new, mandatory section is added unconditionally."""
    OPERATIONS["section_added"](
        sections, {"path": ["IO"], "value": {"VERBOSITY": "standard"}}
    )
    assert sections["IO"] == {"VERBOSITY": "standard"}


def test_section_added_does_not_overwrite(sections):
    """Test that an already present section is left untouched."""
    OPERATIONS["section_added"](
        sections,
        {"path": ["STRUCTURAL DYNAMIC"], "value": {"DYNAMICTYPE": "OtherValue"}},
    )
    assert sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYPE": "Statics"}


def test_section_added_restrict_to_problemtypes_matching(sections):
    """Test that the section is added if the current problem type is listed."""
    sections["PROBLEM TYPE"] = {"PROBLEMTYPE": "Structure"}
    OPERATIONS["section_added"](
        sections,
        {
            "path": ["IO"],
            "value": {"VERBOSITY": "standard"},
            "restrict_to_problemtypes": ["Structure", "Fluid"],
        },
    )
    assert sections["IO"] == {"VERBOSITY": "standard"}


def test_section_added_restrict_to_problemtypes_not_matching(sections):
    """Test that the section is not added if the current problem type is not
    listed."""
    sections["PROBLEM TYPE"] = {"PROBLEMTYPE": "Fluid"}
    OPERATIONS["section_added"](
        sections,
        {
            "path": ["IO"],
            "value": {"VERBOSITY": "standard"},
            "restrict_to_problemtypes": ["Structure"],
        },
    )
    assert "IO" not in sections


def test_section_added_restrict_to_problemtypes_missing_problemtype(sections):
    """Test that the section is added if no problem type is set at all."""
    OPERATIONS["section_added"](
        sections,
        {
            "path": ["IO"],
            "value": {"VERBOSITY": "standard"},
            "restrict_to_problemtypes": ["Structure"],
        },
    )
    assert sections["IO"] == {"VERBOSITY": "standard"}


def test_section_added_restrict_to_problemtypes_empty_list(sections):
    """Test that an empty restrict_to_problemtypes list behaves as
    unrestricted."""
    sections["PROBLEM TYPE"] = {"PROBLEMTYPE": "Fluid"}
    OPERATIONS["section_added"](
        sections,
        {
            "path": ["IO"],
            "value": {"VERBOSITY": "standard"},
            "restrict_to_problemtypes": [],
        },
    )
    assert sections["IO"] == {"VERBOSITY": "standard"}


def test_section_merged_into_existing(sections):
    """Test merging a section's parameters into an already existing section."""
    sections["OLD_SECTION"] = {"FOO": 1}
    OPERATIONS["section_merged"](
        sections, {"old_path": ["OLD_SECTION"], "new_path": ["STRUCTURAL DYNAMIC"]}
    )
    assert "OLD_SECTION" not in sections
    assert sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYPE": "Statics", "FOO": 1}


def test_section_merged_into_new(sections):
    """Test merging a section's parameters into a not yet existing section."""
    sections["OLD_SECTION"] = {"FOO": 1}
    OPERATIONS["section_merged"](
        sections, {"old_path": ["OLD_SECTION"], "new_path": ["BRAND_NEW"]}
    )
    assert "OLD_SECTION" not in sections
    assert sections["BRAND_NEW"] == {"FOO": 1}


def test_section_merged_absent_is_noop(sections):
    """Test that merging an already-absent section does not raise."""
    OPERATIONS["section_merged"](
        sections, {"old_path": ["DOES_NOT_EXIST"], "new_path": ["STRUCTURAL DYNAMIC"]}
    )


def test_section_merged_key_collision_raises(sections):
    """Test that a key collision in the target section raises."""
    sections["OLD_SECTION"] = {"DYNAMICTYPE": "Dynamic"}
    with pytest.raises(MigrationError):
        OPERATIONS["section_merged"](
            sections,
            {"old_path": ["OLD_SECTION"], "new_path": ["STRUCTURAL DYNAMIC"]},
        )


def test_section_merged_non_dict_source_raises(sections):
    """Test that merging a non-dict value raises."""
    sections["OLD_SECTION"] = "not-a-dict"
    with pytest.raises(MigrationError):
        OPERATIONS["section_merged"](
            sections, {"old_path": ["OLD_SECTION"], "new_path": ["BRAND_NEW"]}
        )


def test_parameter_moved(sections):
    """Test moving a single parameter to a new location."""
    OPERATIONS["parameter_moved"](
        sections,
        {
            "old_path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
            "new_path": ["IO", "DYNAMICTYPE"],
        },
    )
    assert "DYNAMICTYPE" not in sections["STRUCTURAL DYNAMIC"]
    assert sections["IO"] == {"DYNAMICTYPE": "Statics"}


def test_parameter_moved_absent_is_noop(sections):
    """Test that moving an already-absent parameter does not raise."""
    OPERATIONS["parameter_moved"](
        sections,
        {"old_path": ["DOES_NOT_EXIST", "PARAM"], "new_path": ["IO", "PARAM"]},
    )
    assert "IO" not in sections


def test_parameter_moved_ambiguous_raises(sections):
    """Test that moving a fanned-out parameter with several matches raises."""
    with pytest.raises(MigrationError):
        OPERATIONS["parameter_moved"](
            sections,
            {
                "old_path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
                "new_path": ["IO", "NUMMAT"],
            },
        )


def test_parameter_moved_target_collision_raises(sections):
    """Test that moving into an already occupied target raises."""
    sections["IO"] = {"DYNAMICTYPE": "Existing"}
    with pytest.raises(MigrationError):
        OPERATIONS["parameter_moved"](
            sections,
            {
                "old_path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
                "new_path": ["IO", "DYNAMICTYPE"],
            },
        )


def test_parameter_moved_blocked_by_non_dict_intermediate_raises(sections):
    """Test that a non-dict value blocking the target path raises."""
    with pytest.raises(MigrationError):
        OPERATIONS["parameter_moved"](
            sections,
            {
                "old_path": ["MATERIALS", "MAT_StVenantKirchhoff", "NUE"],
                # "DYNAMICTYPE" is a string, not a dict, and thus blocks the path.
                "new_path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE", "NUE"],
            },
        )


def test_parameter_value_renamed(sections):
    """Test remapping an enum-like parameter value."""
    OPERATIONS["parameter_value_renamed"](
        sections,
        {
            "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
            "value_map": {"Statics": "Static"},
        },
    )
    assert sections["STRUCTURAL DYNAMIC"]["DYNAMICTYPE"] == "Static"


def test_parameter_value_renamed_unmapped_value_untouched(sections):
    """Test that unmapped values are left untouched."""
    OPERATIONS["parameter_value_renamed"](
        sections,
        {
            "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
            "value_map": {"SomeOtherValue": "Whatever"},
        },
    )
    assert sections["STRUCTURAL DYNAMIC"]["DYNAMICTYPE"] == "Statics"
