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
"""Apply the migration database to an input file's sections.

This module deliberately only depends on `fourcipp.utils.yaml_io` and does not require a
configured 4C metadata/schema (`fourcipp.CONFIG`), so it can migrate an input file even
without a working 4C build. Use of `input_version`/migration is entirely optional: an input
file without `input_version` set is simply treated as being on the oldest known version.
"""

import copy
import pathlib
from dataclasses import dataclass, field

from fourcipp.migration.database import (
    Version,
    load_migration_database,
    parse_version,
    select_migrations,
)
from fourcipp.migration.operations import OPERATIONS
from fourcipp.utils.type_hinting import Path
from fourcipp.utils.yaml_io import dump_yaml, load_yaml

DEFAULT_MIGRATIONS_DIR = pathlib.Path(__file__).parent / "migrations"
# Bundled, versioned migration database shipped with FourCIPP.


def _version_string(version: Version | None) -> str:
    """Format a version tuple as a `MAJOR.MINOR.PATCH` string.

    Args:
        version: Version to format, or `None`

    Returns:
        The formatted version, or `"unknown"` if `version` is `None`
    """
    if version is None:
        return "unknown"
    return ".".join(str(part) for part in version)


@dataclass
class MigrationReport:
    """Summary of a migration run.

    Attributes:
        from_version: Version the input file was migrated from, or `None` if unknown
        to_version: Version the input file was migrated to
        applied: Human-readable description of every migration entry that changed the data
    """

    from_version: Version | None
    to_version: Version | None
    applied: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        """Whether any migration entry actually modified the input file.

        Returns:
            True if at least one migration entry was applied
        """
        return bool(self.applied)

    def __str__(self) -> str:
        """Human-readable, multi-line summary of the migration report.

        Returns:
            The formatted report
        """
        lines = [
            f"Migrated input file from version {_version_string(self.from_version)} to "
            f"{_version_string(self.to_version)}."
        ]

        if self.applied:
            lines.append("Applied migrations:")
            lines.extend(f"  - {description}" for description in self.applied)
        else:
            lines.append("No migrations were applied.")

        return "\n".join(lines)


def migrate_sections(
    sections: dict,
    database: dict[Version, list[dict]],
    to_version: Version | None = None,
) -> MigrationReport:
    """Migrate a raw, nested `sections` dict in place using a migration
    database.

    Args:
        sections: Nested input file data, as returned by `fourcipp.utils.yaml_io.load_yaml`
        database: Migration database, as returned by
            `fourcipp.migration.database.load_migration_database`
        to_version: Version to migrate to (inclusive); defaults to the newest known version

    Returns:
        A report of the applied migrations

    Raises:
        MigrationError: If a migration entry cannot be applied, see the individual operation
            handlers in `fourcipp.migration.operations`
    """
    input_version_string = sections.get("input_version")
    from_version = parse_version(input_version_string) if input_version_string else None

    # Resolve the target version upfront: default to the newest known migration, falling back
    # to the file's own version if the database is empty (e.g. no migrations bundled yet).
    effective_to_version = to_version
    if effective_to_version is None:
        effective_to_version = max(database) if database else from_version

    report = MigrationReport(from_version=from_version, to_version=effective_to_version)

    if effective_to_version is not None:
        applicable = select_migrations(database, from_version, effective_to_version)

        for _, entries in applicable:
            for entry in entries:
                before = copy.deepcopy(sections)
                OPERATIONS[entry["type"]](sections, entry)
                if sections != before:
                    report.applied.append(f"[{entry['id']}] {entry['description']}")

        # Never move backwards: the file may already be newer than the requested/known target.
        if from_version is not None and from_version > effective_to_version:
            effective_to_version = from_version
            report.to_version = effective_to_version

        sections["input_version"] = _version_string(effective_to_version)

    return report


def migrate_file(
    input_path: Path,
    output_path: Path,
    migrations_dir: Path | None = None,
    to_version: str | None = None,
) -> MigrationReport:
    """Migrate a 4C input file on disk to a newer input file version.

    Args:
        input_path: Path to the input file to migrate
        output_path: Path to write the migrated input file to (may be the same as
            `input_path` to migrate in place)
        migrations_dir: Directory containing `<version>.yaml` migration files; defaults to
            the migration database bundled with FourCIPP
        to_version: Version to migrate to (inclusive), as a `MAJOR.MINOR.PATCH` string;
            defaults to the newest known version

    Returns:
        A report of the applied migrations
    """
    database = load_migration_database(migrations_dir or DEFAULT_MIGRATIONS_DIR)
    sections = load_yaml(input_path)

    report = migrate_sections(
        sections,
        database,
        parse_version(to_version) if to_version is not None else None,
    )

    dump_yaml(sections, output_path)

    return report
