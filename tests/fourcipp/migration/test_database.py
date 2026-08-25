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
"""Test the migration database loading and validation."""

import pytest

from fourcipp.migration.database import (
    KNOWN_TYPES,
    load_migration_database,
    load_migration_file,
    parse_version,
    select_migrations,
    validate_entry,
)
from fourcipp.migration.errors import MigrationError
from fourcipp.utils.yaml_io import dump_yaml


@pytest.mark.parametrize(
    "version_string, expected",
    [
        ("1.0.0", (1, 0, 0)),
        ("2.13.4", (2, 13, 4)),
        (" 1.2.3 ", (1, 2, 3)),
    ],
)
def test_parse_version(version_string, expected):
    """Test parsing valid version strings."""
    assert parse_version(version_string) == expected


@pytest.mark.parametrize("version_string", ["1.0", "1.0.0.0", "a.b.c", "", "1.0.0-rc1"])
def test_parse_version_invalid_raises(version_string):
    """Test that invalid version strings raise."""
    with pytest.raises(MigrationError):
        parse_version(version_string)


def test_known_types_include_removed_no_replacement():
    """Test that `removed_no_replacement` is a known, but not auto-fix,
    type."""
    assert "removed_no_replacement" in KNOWN_TYPES


@pytest.mark.parametrize(
    "entry",
    [
        {
            "id": "remove-nummat",
            "type": "parameter_removed",
            "description": "Remove NUMMAT.",
            "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
        },
        {
            "id": "rename-dynamictype",
            "type": "parameter_renamed",
            "description": "Rename DYNAMICTYPE.",
            "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
            "new_name": "DYNAMICTYP",
        },
        {
            "id": "flag-old-feature",
            "type": "removed_no_replacement",
            "description": "Old feature was removed.",
            "path": ["OLD_SECTION", "OLD_PARAM"],
            "message": "Please contact the developers for a replacement.",
        },
    ],
)
def test_validate_entry_valid(entry):
    """Test that valid entries pass validation."""
    validate_entry(entry)


def test_validate_entry_missing_universal_field_raises():
    """Test that a missing universal field (e.g. description) raises."""
    with pytest.raises(MigrationError):
        validate_entry(
            {
                "id": "remove-nummat",
                "type": "parameter_removed",
                "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
            }
        )


def test_validate_entry_unknown_type_raises():
    """Test that an unknown migration type raises."""
    with pytest.raises(MigrationError):
        validate_entry(
            {
                "id": "some-id",
                "type": "not_a_real_type",
                "description": "Some description.",
            }
        )


def test_validate_entry_missing_type_specific_field_raises():
    """Test that a missing type-specific field (e.g. new_name) raises."""
    with pytest.raises(MigrationError):
        validate_entry(
            {
                "id": "rename-dynamictype",
                "type": "parameter_renamed",
                "description": "Rename DYNAMICTYPE.",
                "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
            }
        )


def test_load_migration_file(tmp_path):
    """Test loading and validating a migration file."""
    migration_file = tmp_path / "1.1.0.yaml"
    dump_yaml(
        {
            "migrations": [
                {
                    "id": "remove-nummat",
                    "type": "parameter_removed",
                    "description": "Remove NUMMAT.",
                    "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
                }
            ]
        },
        migration_file,
    )
    entries = load_migration_file(migration_file)
    assert len(entries) == 1
    assert entries[0]["id"] == "remove-nummat"


def test_load_migration_file_without_migrations_key_raises(tmp_path):
    """Test that a file without a top-level `migrations` list raises."""
    migration_file = tmp_path / "1.1.0.yaml"
    dump_yaml({"not_migrations": []}, migration_file)
    with pytest.raises(MigrationError):
        load_migration_file(migration_file)


def test_load_migration_file_invalid_entry_raises(tmp_path):
    """Test that an invalid entry within the file raises."""
    migration_file = tmp_path / "1.1.0.yaml"
    dump_yaml(
        {"migrations": [{"id": "bad-entry", "type": "parameter_removed"}]},
        migration_file,
    )
    with pytest.raises(MigrationError):
        load_migration_file(migration_file)


def test_load_migration_database(tmp_path):
    """Test loading a directory of migration files, keyed by target version."""
    dump_yaml(
        {
            "migrations": [
                {
                    "id": "remove-nummat",
                    "type": "parameter_removed",
                    "description": "Remove NUMMAT.",
                    "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
                }
            ]
        },
        tmp_path / "1.1.0.yaml",
    )
    dump_yaml(
        {
            "migrations": [
                {
                    "id": "rename-dynamictype",
                    "type": "parameter_renamed",
                    "description": "Rename DYNAMICTYPE.",
                    "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
                    "new_name": "DYNAMICTYP",
                }
            ]
        },
        tmp_path / "1.2.0.yaml",
    )

    database = load_migration_database(tmp_path)

    assert set(database) == {(1, 1, 0), (1, 2, 0)}
    assert database[(1, 1, 0)][0]["id"] == "remove-nummat"
    assert database[(1, 2, 0)][0]["id"] == "rename-dynamictype"


def test_load_migration_database_empty_dir(tmp_path):
    """Test that an empty migrations directory yields an empty database."""
    assert load_migration_database(tmp_path) == {}


def test_load_migration_database_duplicate_version_raises(tmp_path):
    """Test that two files targeting the same version raise."""
    # Same stem, different casing cannot collide on most filesystems, so instead we
    # directly provoke the duplicate check by writing to the same file twice would not work.
    # Two distinct extensions could exist in principle; simulate this via a name collision
    # after parsing by using the exact same version string via different formatting.
    dump_yaml(
        {
            "migrations": [
                {
                    "id": "a",
                    "type": "parameter_removed",
                    "description": "d",
                    "path": ["A"],
                }
            ]
        },
        tmp_path / "1.1.0.yaml",
    )
    # Manually insert a second file with a name that parses to the same version tuple.
    (tmp_path / "01.1.0.yaml").write_text("migrations: []\n")

    with pytest.raises(MigrationError):
        load_migration_database(tmp_path)


@pytest.mark.parametrize(
    "from_version, to_version, expected_versions",
    [
        (None, None, [(1, 0, 0), (1, 1, 0), (1, 2, 0)]),
        ((1, 0, 0), None, [(1, 1, 0), (1, 2, 0)]),
        ((1, 0, 0), (1, 1, 0), [(1, 1, 0)]),
        ((1, 2, 0), None, []),
        ((1, 5, 0), None, []),
    ],
)
def test_select_migrations(from_version, to_version, expected_versions):
    """Test selecting the applicable, half-open version range of migrations."""
    database = {
        (1, 0, 0): [{"id": "a"}],
        (1, 1, 0): [{"id": "b"}],
        (1, 2, 0): [{"id": "c"}],
    }
    selected = select_migrations(database, from_version, to_version)
    assert [version for version, _ in selected] == expected_versions


def test_select_migrations_empty_database():
    """Test that selecting from an empty database returns nothing."""
    assert select_migrations({}, None, None) == []
