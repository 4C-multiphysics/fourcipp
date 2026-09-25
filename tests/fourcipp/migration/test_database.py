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

from pathlib import Path

import pytest

from fourcipp.migration.database import (
    format_version,
    load_migration_database,
    load_migration_file,
    parse_version,
    select_migrations,
    validate_entry,
)
from fourcipp.migration.errors import MigrationError
from fourcipp.utils.yaml_io import dump_yaml


@pytest.mark.parametrize(
    "version, expected",
    [
        ("00000", 0),
        ("00001", 1),
        ("00042", 42),
        ("99999", 99999),
        # Versions beyond the padding width are not truncated.
        ("123456", 123456),
        # Unpadded input is accepted, so '--to-version 2' works.
        ("2", 2),
        (" 00002 ", 2),
        # A hand-written, unquoted `input_version` is loaded from YAML as an int.
        (2, 2),
        (0, 0),
    ],
)
def test_parse_version(version, expected):
    """Test parsing valid versions."""
    assert parse_version(version) == expected


@pytest.mark.parametrize(
    "version",
    # Dotted versions are not special-cased: they are simply not valid numbers.
    ["1.0.0", "1.0", "a", "", "  ", "1e3", "-1", "0x1", -1, 1.5, None, True],
)
def test_parse_version_invalid_raises(version):
    """Test that invalid versions raise."""
    with pytest.raises(MigrationError):
        parse_version(version)


@pytest.mark.parametrize(
    "version, expected",
    [(0, "00000"), (1, "00001"), (42, "00042"), (99999, "99999"), (123456, "123456")],
)
def test_format_version(version, expected):
    """Test that versions are zero-padded to a fixed width."""
    assert format_version(version) == expected


def test_format_version_round_trip():
    """Test that formatting and parsing are inverse operations."""
    for version in (0, 1, 7, 99999, 100000):
        assert parse_version(format_version(version)) == version


def test_format_version_sorts_identically_as_text_and_number():
    """Test that zero padding keeps textual and numeric ordering identical."""
    versions = [3, 11, 0, 99999, 2, 100]
    assert [parse_version(v) for v in sorted(format_version(v) for v in versions)] == (
        sorted(versions)
    )


@pytest.mark.parametrize(
    "entry",
    [
        {
            "type": "parameter_removed",
            "description": "Remove NUMMAT.",
            "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
        },
        {
            "type": "parameter_renamed",
            "description": "Rename DYNAMICTYPE.",
            "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
            "new_name": "DYNAMICTYP",
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
                "type": "parameter_removed",
                "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
            }
        )


def test_validate_entry_unknown_type_raises():
    """Test that an unknown migration type raises."""
    with pytest.raises(MigrationError):
        validate_entry(
            {
                "type": "not_a_real_type",
                "description": "Some description.",
            }
        )


def test_validate_entry_missing_type_specific_field_raises():
    """Test that a missing type-specific field (e.g. new_name) raises."""
    with pytest.raises(MigrationError):
        validate_entry(
            {
                "type": "parameter_renamed",
                "description": "Rename DYNAMICTYPE.",
                "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
            }
        )


def test_validate_entry_non_mapping_raises():
    """Test that a list item that is not a mapping raises."""
    with pytest.raises(MigrationError, match="must be a mapping, got str"):
        validate_entry("just a string")


def test_validate_entry_error_reports_position_source_and_entry():
    """Test that errors locate the entry by position, file and full content."""
    entry = {
        "type": "parameter_renamed",
        "description": "Rename DYNAMICTYPE.",
        "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
    }
    with pytest.raises(MigrationError) as excinfo:
        validate_entry(entry, position=3, source=Path("00002.yaml"))

    message = str(excinfo.value)
    assert "Migration entry 3 in '00002.yaml'" in message
    assert "['new_name']" in message
    assert str(entry) in message


def test_load_migration_file_error_reports_one_based_position(tmp_path):
    """Test that the reported position is the 1-based index within the file."""
    migration_file = tmp_path / "00001.yaml"
    dump_yaml(
        {
            "migrations": [
                {
                    "type": "parameter_removed",
                    "description": "Remove NUMMAT.",
                    "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
                },
                {"type": "parameter_removed", "description": "Missing its path."},
            ]
        },
        migration_file,
    )
    with pytest.raises(MigrationError, match="Migration entry 2 in "):
        load_migration_file(migration_file)


def test_load_migration_file(tmp_path):
    """Test loading and validating a migration file."""
    migration_file = tmp_path / "00001.yaml"
    dump_yaml(
        {
            "migrations": [
                {
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
    assert entries[0]["description"] == "Remove NUMMAT."


def test_load_migration_file_without_migrations_key_raises(tmp_path):
    """Test that a file without a top-level `migrations` list raises."""
    migration_file = tmp_path / "00001.yaml"
    dump_yaml({"not_migrations": []}, migration_file)
    with pytest.raises(MigrationError):
        load_migration_file(migration_file)


def test_load_migration_file_invalid_entry_raises(tmp_path):
    """Test that an invalid entry within the file raises."""
    migration_file = tmp_path / "00001.yaml"
    dump_yaml(
        {"migrations": [{"type": "parameter_removed"}]},
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
                    "type": "parameter_removed",
                    "description": "Remove NUMMAT.",
                    "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
                }
            ]
        },
        tmp_path / "00001.yaml",
    )
    dump_yaml(
        {
            "migrations": [
                {
                    "type": "parameter_renamed",
                    "description": "Rename DYNAMICTYPE.",
                    "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
                    "new_name": "DYNAMICTYP",
                }
            ]
        },
        tmp_path / "00002.yaml",
    )

    database = load_migration_database(tmp_path)

    assert set(database) == {1, 2}
    assert database[1][0]["description"] == "Remove NUMMAT."
    assert database[2][0]["description"] == "Rename DYNAMICTYPE."


def test_load_migration_database_skips_non_version_files(tmp_path):
    """Test that YAML files not named after a version are ignored."""
    dump_yaml(
        {
            "migrations": [
                {
                    "type": "parameter_removed",
                    "description": "Remove NUMMAT.",
                    "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
                }
            ]
        },
        tmp_path / "00001.yaml",
    )
    # Work-in-progress and unrelated YAML files may live alongside the database. They are
    # skipped rather than rejected, which would break every migration run.
    (tmp_path / "latest_upgrade.yaml").write_text("migrations: []\n")
    (tmp_path / "README.yaml").write_text("not even migrations\n")

    database = load_migration_database(tmp_path)

    assert set(database) == {1}


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
                    "type": "parameter_removed",
                    "description": "d",
                    "path": ["A"],
                }
            ]
        },
        tmp_path / "00001.yaml",
    )
    # Manually insert a second file whose name parses to the same version number.
    (tmp_path / "001.yaml").write_text("migrations: []\n")

    with pytest.raises(MigrationError):
        load_migration_database(tmp_path)


@pytest.mark.parametrize(
    "from_version, to_version, expected_versions",
    [
        (None, None, [0, 1, 2]),
        (0, None, [1, 2]),
        (0, 1, [1]),
        (2, None, []),
        (5, None, []),
    ],
)
def test_select_migrations(from_version, to_version, expected_versions):
    """Test selecting the applicable, half-open version range of migrations."""
    database = {
        0: [{"description": "a"}],
        1: [{"description": "b"}],
        2: [{"description": "c"}],
    }
    selected = select_migrations(database, from_version, to_version)
    assert [version for version, _ in selected] == expected_versions


def test_select_migrations_empty_database():
    """Test that selecting from an empty database returns nothing."""
    assert select_migrations({}, None, None) == []


def test_load_migration_file_preserves_entry_order(tmp_path):
    """Test that loading a migration file preserves the order of its
    entries."""
    migration_file = tmp_path / "00001.yaml"
    dump_yaml(
        {
            "migrations": [
                {
                    "type": "parameter_removed",
                    "description": f"Entry {index}.",
                    "path": ["SECTION", f"PARAM_{index}"],
                }
                for index in range(10)
            ]
        },
        migration_file,
    )

    entries = load_migration_file(migration_file)

    assert [entry["description"] for entry in entries] == [
        f"Entry {index}." for index in range(10)
    ]
