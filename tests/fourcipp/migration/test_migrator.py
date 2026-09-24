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

import copy

import pytest

from fourcipp.migration.errors import MigrationError
from fourcipp.migration.migrator import (
    MigrationReport,
    diff_migration,
    migrate_file,
    migrate_sections,
)
from fourcipp.utils.yaml_io import dump_yaml, load_yaml


@pytest.fixture(name="database")
def fixture_database():
    """Small, two-version migration database exercising several entry types."""
    return {
        1: [
            {
                "type": "parameter_removed",
                "description": "NUMMAT is redundant with the length of MATIDS.",
                "path": ["MATERIALS", "MAT_ElastHyper", "NUMMAT"],
            }
        ],
        2: [
            {
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
    assert sections["input_version"] == "00002"

    assert report.from_version is None
    assert report.to_version == 2
    assert report.changed
    assert len(report.applied) == 2


def test_migrate_sections_is_idempotent(sections, database):
    """Test that migrating an already-migrated file is a no-op the second
    time."""
    migrate_sections(sections, database)
    report = migrate_sections(sections, database)

    assert not report.changed
    assert report.from_version == 2
    assert report.to_version == 2


def test_migrate_sections_partial_from_version(database):
    """Test that only migrations newer than the file's own version are
    applied."""
    sections = {
        "MATERIALS": [
            {"MAT": 1, "MAT_ElastHyper": {"NUMMAT": 2, "MATIDS": [10, 11]}},
        ],
        "STRUCTURAL DYNAMIC": {"DYNAMICTYPE": "Statics"},
        "input_version": "00001",
    }

    report = migrate_sections(sections, database)

    assert "NUMMAT" in sections["MATERIALS"][0]["MAT_ElastHyper"]
    assert sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYP": "Statics"}
    assert report.from_version == 1
    assert len(report.applied) == 1


def test_migrate_sections_to_version_limits_range(sections, database):
    """Test that `to_version` limits which migrations are applied."""
    report = migrate_sections(sections, database, to_version=1)

    assert "NUMMAT" not in sections["MATERIALS"][0]["MAT_ElastHyper"]
    assert sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYPE": "Statics"}
    assert sections["input_version"] == "00001"
    assert report.to_version == 1


def test_migrate_sections_clamps_to_version_to_newest_known(sections, database):
    """Test that a target version newer than the database is clamped to its
    newest version."""
    report = migrate_sections(sections, database, to_version=99999)

    # All known migrations are applied, but the file is not stamped 99999: doing so would
    # make future migrations up to 99999 look like they had already been applied.
    assert sections["input_version"] == "00002"
    assert report.to_version == 2
    assert report.clamped_from == 99999
    assert "99999" in report.clamp_warning
    assert "00002" in report.clamp_warning


def test_migrate_sections_clamped_to_version_never_downgrades(database):
    """Test that clamping does not downgrade a file newer than the database."""
    sections = {"input_version": "00099"}
    report = migrate_sections(sections, database, to_version=99999)

    assert sections["input_version"] == "00099"
    assert report.to_version == 99
    assert report.clamped_from == 99999


def test_migrate_sections_to_version_within_database_is_not_clamped(sections, database):
    """Test that a target version the database knows about is used as is."""
    report = migrate_sections(sections, database, to_version=1)

    assert report.clamped_from is None
    assert report.clamp_warning is None


def test_migrate_sections_failure_leaves_sections_untouched(database):
    """Test that a failing migration entry rolls back all earlier ones."""
    database[2][0] = {
        "type": "section_renamed",
        "description": "Renames onto an already existing section.",
        "path": ["STRUCTURAL DYNAMIC"],
        "new_name": "SOLVER",
    }
    sections = {
        "MATERIALS": [
            {"MAT": 1, "MAT_ElastHyper": {"NUMMAT": 2, "MATIDS": [10, 11]}},
        ],
        "STRUCTURAL DYNAMIC": {"DYNAMICTYPE": "Statics"},
        "SOLVER": {"NAME": "Structure_Solver"},
        "input_version": "00000",
    }
    original = copy.deepcopy(sections)

    with pytest.raises(MigrationError):
        migrate_sections(sections, database)

    # The 00001 migration succeeded before the 00002 one failed, but must not persist.
    assert sections == original


def test_migrate_sections_never_downgrades_version(database):
    """Test that a file newer than the database's newest version is
    untouched."""
    sections = {"input_version": "00099"}
    report = migrate_sections(sections, database)

    assert sections["input_version"] == "00099"
    assert not report.changed
    assert report.to_version == 99


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

    assert "00002" in report_string
    assert "NUMMAT is redundant with the length of MATIDS." in report_string
    assert "DYNAMICTYPE was renamed." in report_string


def test_migration_report_str_no_migrations_applied():
    """Test the report's string representation when nothing was applied."""
    report = MigrationReport(from_version=0, to_version=0)
    assert "No migrations were applied." in str(report)


def test_migrate_file(tmp_path, sections, database):
    """Test migrating an input file on disk."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    dump_yaml({"migrations": database[1]}, migrations_dir / "00001.yaml")
    dump_yaml({"migrations": database[2]}, migrations_dir / "00002.yaml")

    input_path = tmp_path / "input.4C.yaml"
    dump_yaml(sections, input_path)

    output_path = tmp_path / "input_migrated.4C.yaml"
    report = migrate_file(input_path, output_path, migrations_dir)

    migrated_sections = load_yaml(output_path)
    assert "NUMMAT" not in migrated_sections["MATERIALS"][0]["MAT_ElastHyper"]
    assert migrated_sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYP": "Statics"}
    assert migrated_sections["input_version"] == "00002"
    assert report.changed

    # The original input file is untouched, since output_path != input_path.
    original_sections = load_yaml(input_path)
    assert "input_version" not in original_sections


def test_migrate_file_in_place(tmp_path, sections, database):
    """Test migrating an input file in place, overwriting the original."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    dump_yaml({"migrations": database[1]}, migrations_dir / "00001.yaml")

    input_path = tmp_path / "input.4C.yaml"
    dump_yaml(sections, input_path)

    migrate_file(input_path, input_path, migrations_dir)

    migrated_sections = load_yaml(input_path)
    assert "NUMMAT" not in migrated_sections["MATERIALS"][0]["MAT_ElastHyper"]
    assert migrated_sections["input_version"] == "00001"


def test_migrate_file_to_version_as_string(tmp_path, sections, database):
    """Test that `to_version` can be passed as a version string."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    dump_yaml({"migrations": database[1]}, migrations_dir / "00001.yaml")
    dump_yaml({"migrations": database[2]}, migrations_dir / "00002.yaml")

    input_path = tmp_path / "input.4C.yaml"
    dump_yaml(sections, input_path)

    output_path = tmp_path / "output.4C.yaml"
    report = migrate_file(input_path, output_path, migrations_dir, to_version="00001")

    assert report.to_version == 1
    migrated_sections = load_yaml(output_path)
    assert migrated_sections["STRUCTURAL DYNAMIC"] == {"DYNAMICTYPE": "Statics"}


@pytest.fixture(name="migrations_dir")
def fixture_migrations_dir(tmp_path, database):
    """Migration database fixture written to disk."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    dump_yaml({"migrations": database[1]}, migrations_dir / "00001.yaml")
    dump_yaml({"migrations": database[2]}, migrations_dir / "00002.yaml")
    return migrations_dir


def test_diff_migration_writes_nothing(tmp_path, sections, migrations_dir):
    """Test that a diff run leaves the input file and its directory
    untouched."""
    input_path = tmp_path / "input.4C.yaml"
    dump_yaml(sections, input_path)
    original = input_path.read_text(encoding="utf-8")
    files_before = sorted(p.name for p in tmp_path.iterdir())

    report, diff = diff_migration(input_path, migrations_dir)

    assert input_path.read_text(encoding="utf-8") == original
    assert sorted(p.name for p in tmp_path.iterdir()) == files_before
    assert report.changed
    assert diff


def test_diff_migration_shows_only_semantic_changes(tmp_path, sections, migrations_dir):
    """Test that the diff contains the migration changes, not formatting
    noise."""
    input_path = tmp_path / "input.4C.yaml"
    dump_yaml(sections, input_path)

    _, diff = diff_migration(input_path, migrations_dir)

    changed_lines = [
        line
        for line in diff.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    ]
    # Exactly the two migrations and the added version stamp, nothing else.
    assert any(line.startswith("-") and "NUMMAT" in line for line in changed_lines)
    assert any(line.startswith("-") and "DYNAMICTYPE" in line for line in changed_lines)
    assert any(line.startswith("+") and "DYNAMICTYP:" in line for line in changed_lines)
    assert any(
        line.startswith("+") and "input_version" in line for line in changed_lines
    )
    assert len(changed_lines) == 4


def test_diff_migration_ignores_comments_and_quoting(tmp_path, migrations_dir):
    """Test that round-trip-only differences do not show up in the diff."""
    input_path = tmp_path / "input.4C.yaml"
    # Comments and unquoted scalars are lost/normalized by the YAML round-trip, but that is
    # not a migration change and must not appear in the diff.
    input_path.write_text(
        "# a comment that the round-trip drops\n"
        "input_version: '00002'\n"
        "STRUCTURAL DYNAMIC:\n"
        "  DYNAMICTYP: Statics\n",
        encoding="utf-8",
    )

    report, diff = diff_migration(input_path, migrations_dir)

    assert not report.changed
    assert diff == ""


def test_diff_migration_reports_version_stamp_only(tmp_path, migrations_dir):
    """Test that a file needing no migration still shows its version stamp."""
    input_path = tmp_path / "input.4C.yaml"
    dump_yaml({"STRUCTURAL DYNAMIC": {"DYNAMICTYP": "Statics"}}, input_path)

    report, diff = diff_migration(input_path, migrations_dir)

    assert not report.changed
    assert "+input_version" in diff


def test_diff_migration_failure_writes_nothing(tmp_path, sections, database):
    """Test that a failing migration leaves the input file untouched."""
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    dump_yaml({"migrations": database[1]}, migrations_dir / "00001.yaml")
    dump_yaml(
        {
            "migrations": [
                {
                    "type": "section_renamed",
                    "description": "Renames onto an already existing section.",
                    "path": ["STRUCTURAL DYNAMIC"],
                    "new_name": "MATERIALS",
                }
            ]
        },
        migrations_dir / "00002.yaml",
    )

    input_path = tmp_path / "input.4C.yaml"
    dump_yaml(sections, input_path)
    original = input_path.read_text(encoding="utf-8")

    with pytest.raises(MigrationError):
        diff_migration(input_path, migrations_dir)

    assert input_path.read_text(encoding="utf-8") == original


def test_migrate_sections_detects_changes_without_copying_untouched_sections(database):
    """Test that change detection is exact for sections no migration touches.

    Large node/element sections are the bulk of real 4C input files and
    are untouched by these migrations, so they must neither be reported
    as changed nor be deep-copied per migration entry.
    """
    node_coords = [f"NODE {i} COORD 0.0 0.0 {i}" for i in range(100)]
    sections = {
        "input_version": "00000",
        "NODE COORDS": list(node_coords),
        "MATERIALS": [
            {"MAT": 1, "MAT_ElastHyper": {"NUMMAT": 2, "MATIDS": [10, 11]}},
        ],
        "STRUCTURAL DYNAMIC": {"DYNAMICTYPE": "Statics"},
    }

    report = migrate_sections(sections, database)

    assert sections["NODE COORDS"] == node_coords
    # Both migrations are still detected, and neither of them targets NODE COORDS.
    assert len(report.applied) == 2


def test_migrate_sections_does_not_report_noop_entries(database):
    """Test that entries matching nothing are not reported as applied."""
    database[1][0]["path"] = ["MATERIALS", "MAT_DoesNotExist", "NUMMAT"]
    sections = {
        "input_version": "00000",
        "MATERIALS": [
            {"MAT": 1, "MAT_ElastHyper": {"NUMMAT": 2, "MATIDS": [10, 11]}},
        ],
        "STRUCTURAL DYNAMIC": {"DYNAMICTYPE": "Statics"},
    }

    report = migrate_sections(sections, database)

    assert report.applied == ["DYNAMICTYPE was renamed."]
    assert sections["MATERIALS"][0]["MAT_ElastHyper"]["NUMMAT"] == 2


def test_migrate_sections_detects_cross_section_move():
    """Test change detection for an entry touching two different sections."""
    database = {
        1: [
            {
                "type": "parameter_moved",
                "description": "Moved to another section.",
                "old_path": ["OLD SECTION", "PARAM"],
                "new_path": ["NEW SECTION", "PARAM"],
            }
        ]
    }
    sections = {"OLD SECTION": {"PARAM": 1}, "NEW SECTION": {"OTHER": 2}}

    report = migrate_sections(sections, database)

    assert sections["NEW SECTION"] == {"OTHER": 2, "PARAM": 1}
    assert "OLD SECTION" not in sections or "PARAM" not in sections["OLD SECTION"]
    assert len(report.applied) == 1


def test_migrate_sections_applies_entries_in_file_order():
    """Test that entries within one version are applied in the order listed.

    The two renames form a chain (A -> B -> C), so applying them in the
    listed order yields C, while any other order leaves the intermediate
    B behind.
    """
    database = {
        1: [
            {
                "type": "parameter_renamed",
                "description": "A was renamed to B.",
                "path": ["SECTION", "A"],
                "new_name": "B",
            },
            {
                "type": "parameter_renamed",
                "description": "B was renamed to C.",
                "path": ["SECTION", "B"],
                "new_name": "C",
            },
        ]
    }
    sections = {"SECTION": {"A": 1}}

    report = migrate_sections(sections, database)

    assert sections["SECTION"] == {"C": 1}
    assert report.applied == ["A was renamed to B.", "B was renamed to C."]


def test_migrate_sections_applies_versions_in_ascending_order():
    """Test that versions are applied in ascending order, not insertion
    order."""
    database = {
        2: [
            {
                "type": "parameter_renamed",
                "description": "B was renamed to C.",
                "path": ["SECTION", "B"],
                "new_name": "C",
            }
        ],
        1: [
            {
                "type": "parameter_renamed",
                "description": "A was renamed to B.",
                "path": ["SECTION", "A"],
                "new_name": "B",
            }
        ],
    }
    sections = {"SECTION": {"A": 1}}

    report = migrate_sections(sections, database)

    assert sections["SECTION"] == {"C": 1}
    assert report.applied == ["A was renamed to B.", "B was renamed to C."]
