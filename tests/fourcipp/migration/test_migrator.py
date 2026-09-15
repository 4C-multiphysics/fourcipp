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
"""Test the end-to-end migration of input file sections and files."""

import pytest

from fourcipp.migration.migrator import MigrationReport, migrate_file, migrate_sections
from fourcipp.utils.yaml_io import dump_yaml, load_yaml


@pytest.fixture(name="database")
def fixture_database():
    """Small, two-version migration database exercising several entry types."""
    return {
        (1, 1, 0): [
            {
                "id": "remove-nummat",
                "type": "parameter_removed",
                "description": "NUMMAT is redundant with the length of MATIDS.",
                "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
            }
        ],
        (1, 2, 0): [
            {
                "id": "rename-dynamictype",
                "type": "parameter_renamed",
                "description": "DYNAMICTYPE was renamed.",
                "path": ["STRUCTURAL DYNAMIC", "DYNAMICTYPE"],
                "new_name": "DYNAMICTYP",
            },
        ],
    }


@pytest.fixture(name="sections")
def fixture_sections():
    """Sections dict with no `input_version` set yet."""
    return {
        "MATERIALS": [
            {"MAT": 1, "MAT_ElastHyper": {"NUMMAT": 2, "MATIDS": [10, 11]}},
        ],
        "STRUCTURAL DYNAMIC": {"DYNAMICTYPE": "Statics"},
    }


def test_migrate_sections_applies_all_migrations(sections, database):
    """Test that all applicable migrations are applied and reported."""
    report = migrate_sections(sections, database)

    assert "NUMMAT" not in sections["MATERIALS"][0]["MAT_ElastHyper"]
    assert sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYP": "Statics"}
    assert sections["input_version"] == "1.2.0"

    assert report.from_version is None
    assert report.to_version == (1, 2, 0)
    assert report.changed
    assert len(report.applied) == 2


def test_migrate_sections_is_idempotent(sections, database):
    """Test that migrating an already-migrated file is a no-op the second
    time."""
    migrate_sections(sections, database)
    report = migrate_sections(sections, database)

    assert not report.changed
    assert report.from_version == (1, 2, 0)
    assert report.to_version == (1, 2, 0)


def test_migrate_sections_partial_from_version(database):
    """Test that only migrations newer than the file's own version are
    applied."""
    sections = {
        "MATERIALS": [
            {"MAT": 1, "MAT_ElastHyper": {"NUMMAT": 2, "MATIDS": [10, 11]}},
        ],
        "STRUCTURAL DYNAMIC": {"DYNAMICTYPE": "Statics"},
        "input_version": "1.1.0",
    }

    report = migrate_sections(sections, database)

    assert "NUMMAT" in sections["MATERIALS"][0]["MAT_ElastHyper"]
    assert sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYP": "Statics"}
    assert report.from_version == (1, 1, 0)
    assert len(report.applied) == 1


def test_migrate_sections_to_version_limits_range(sections, database):
    """Test that `to_version` limits which migrations are applied."""
    report = migrate_sections(sections, database, to_version=(1, 1, 0))

    assert "NUMMAT" not in sections["MATERIALS"][0]["MAT_ElastHyper"]
    assert sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYPE": "Statics"}
    assert sections["input_version"] == "1.1.0"
    assert report.to_version == (1, 1, 0)


def test_migrate_sections_never_downgrades_version(database):
    """Test that a file newer than the database's newest version is
    untouched."""
    sections = {"input_version": "5.0.0"}
    report = migrate_sections(sections, database)

    assert sections["input_version"] == "5.0.0"
    assert not report.changed
    assert report.to_version == (5, 0, 0)


def test_migrate_sections_empty_database_is_noop():
    """Test that migrating against an empty database leaves the file
    untouched."""
    sections = {"STRUCTURAL DYNAMIC": {"DYNAMICTYPE": "Statics"}}
    report = migrate_sections(sections, {})

    assert "input_version" not in sections
    assert not report.changed
    assert report.to_version is None


def test_migration_report_str_contains_summary(sections, database):
    """Test that the report's string representation mentions applied
    migrations."""
    report = migrate_sections(sections, database)
    report_string = str(report)

    assert "1.2.0" in report_string
    assert "remove-nummat" in report_string
    assert "rename-dynamictype" in report_string


def test_migration_report_str_no_migrations_applied():
    """Test the report's string representation when nothing was applied."""
    report = MigrationReport(from_version=(1, 0, 0), to_version=(1, 0, 0))
    assert "No migrations were applied." in str(report)


def test_migrate_file(tmp_path, sections, database):
    """Test migrating an input file on disk."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    dump_yaml({"migrations": database[(1, 1, 0)]}, migrations_dir / "1.1.0.yaml")
    dump_yaml({"migrations": database[(1, 2, 0)]}, migrations_dir / "1.2.0.yaml")

    input_path = tmp_path / "input.4C.yaml"
    dump_yaml(sections, input_path)

    output_path = tmp_path / "input_migrated.4C.yaml"
    report = migrate_file(input_path, output_path, migrations_dir)

    migrated_sections = load_yaml(output_path)
    assert "NUMMAT" not in migrated_sections["MATERIALS"][0]["MAT_ElastHyper"]
    assert migrated_sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYP": "Statics"}
    assert migrated_sections["input_version"] == "1.2.0"
    assert report.changed

    # The original input file is untouched, since output_path != input_path.
    original_sections = load_yaml(input_path)
    assert "input_version" not in original_sections


def test_migrate_file_in_place(tmp_path, sections, database):
    """Test migrating an input file in place, overwriting the original."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    dump_yaml({"migrations": database[(1, 1, 0)]}, migrations_dir / "1.1.0.yaml")

    input_path = tmp_path / "input.4C.yaml"
    dump_yaml(sections, input_path)

    migrate_file(input_path, input_path, migrations_dir)

    migrated_sections = load_yaml(input_path)
    assert "NUMMAT" not in migrated_sections["MATERIALS"][0]["MAT_ElastHyper"]
    assert migrated_sections["input_version"] == "1.1.0"


def test_migrate_file_to_version_as_string(tmp_path, sections, database):
    """Test that `to_version` can be passed as a `MAJOR.MINOR.PATCH` string."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    dump_yaml({"migrations": database[(1, 1, 0)]}, migrations_dir / "1.1.0.yaml")
    dump_yaml({"migrations": database[(1, 2, 0)]}, migrations_dir / "1.2.0.yaml")

    input_path = tmp_path / "input.4C.yaml"
    dump_yaml(sections, input_path)

    output_path = tmp_path / "output.4C.yaml"
    report = migrate_file(input_path, output_path, migrations_dir, to_version="1.1.0")

    assert report.to_version == (1, 1, 0)
    migrated_sections = load_yaml(output_path)
    assert migrated_sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYPE": "Statics"}
