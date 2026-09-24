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
import difflib
import pathlib
import tempfile
from dataclasses import dataclass, field

from loguru import logger

from fourcipp.migration.database import (
    Version,
    format_version,
    load_migration_database,
    parse_version,
    select_migrations,
)
from fourcipp.migration.operations import OPERATIONS, entry_root_keys
from fourcipp.utils.type_hinting import Path
from fourcipp.utils.yaml_io import dump_yaml, load_yaml

DEFAULT_MIGRATIONS_DIR = pathlib.Path(__file__).parent / "migrations"
# Bundled, versioned migration database shipped with FourCIPP.

IMPLICIT_INPUT_VERSION: Version = 0
# Version an input file without an `input_version` field is assumed to be on, i.e. before
# any migration. Note that migration selection does not rely on this: an absent
# `input_version` selects every known migration, regardless of this value.


def _version_string(version: Version | None) -> str:
    """Format a version as a zero-padded version string.

    Args:
        version: Version to format, or `None`

    Returns:
        The formatted version, or `"unknown"` if `version` is `None`
    """
    if version is None:
        return "unknown"
    return format_version(version)


@dataclass
class MigrationReport:
    """Summary of a migration run.

    Attributes:
        from_version: Version the input file was migrated from, or `None` if unknown
        to_version: Version the input file was migrated to
        applied: Human-readable description of every migration entry that changed the data
        clamped_from: Requested target version that was newer than the newest known
            migration and therefore reduced to `to_version`, or `None` if no clamping
            happened
    """

    from_version: Version | None
    to_version: Version | None
    applied: list[str] = field(default_factory=list)
    clamped_from: Version | None = None

    @property
    def changed(self) -> bool:
        """Whether any migration entry actually modified the input file.

        Returns:
            True if at least one migration entry was applied
        """
        return bool(self.applied)

    @property
    def clamp_warning(self) -> str | None:
        """Warning about a requested target version that could not be honored.

        Returns:
            The formatted warning, or `None` if the requested target version was used as is
        """
        if self.clamped_from is None:
            return None
        return (
            f"Requested version {_version_string(self.clamped_from)} is newer than the "
            "newest known migration. Migrated to "
            f"{_version_string(self.to_version)} instead."
        )

    def __str__(self) -> str:
        """Human-readable, multi-line summary of the migration report.

        Returns:
            The formatted report
        """
        lines = [
            f"Migrated input file from version {_version_string(self.from_version)} to "
            f"{_version_string(self.to_version)}."
        ]

        warning = self.clamp_warning
        if warning is not None:
            lines.append(warning)

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

    The migration is all-or-nothing: it is carried out on a working copy and only committed
    back into `sections` once every migration entry has been applied successfully. If a
    migration entry fails, `sections` is left exactly as it was.

    Args:
        sections: Nested input file data, as returned by `fourcipp.utils.yaml_io.load_yaml`
        database: Migration database, as returned by
            `fourcipp.migration.database.load_migration_database`
        to_version: Version to migrate to (inclusive); defaults to the newest known version.
            A version newer than the newest known migration is clamped to the latter.

    Returns:
        A report of the applied migrations

    Raises:
        MigrationError: If a migration entry cannot be applied, see the individual operation
            handlers in `fourcipp.migration.operations`
    """
    input_version = sections.get("input_version")
    from_version = parse_version(input_version) if input_version is not None else None

    # Resolve the target version upfront: default to the newest known migration, falling back
    # to the file's own version if the database is empty (e.g. no migrations bundled yet).
    newest_known = max(database) if database else None
    clamped_from = None
    effective_to_version = to_version
    if effective_to_version is None:
        effective_to_version = (
            newest_known if newest_known is not None else from_version
        )
    elif newest_known is not None and effective_to_version > newest_known:
        # Never stamp a version we have no migrations for: doing so would make every
        # future migration up to that version look like it had already been applied.
        logger.warning(
            f"Requested target version {_version_string(effective_to_version)} is newer than "
            f"the newest known migration {_version_string(newest_known)}. Migrating to "
            f"{_version_string(newest_known)} instead."
        )
        clamped_from = effective_to_version
        effective_to_version = newest_known

    report = MigrationReport(
        from_version=from_version,
        to_version=effective_to_version,
        clamped_from=clamped_from,
    )

    if effective_to_version is not None:
        applicable = select_migrations(database, from_version, effective_to_version)

        # Migrate a working copy, so a failing handler cannot leave the caller's dict
        # half-migrated (and still carrying its original, now wrong, `input_version`).
        working = copy.deepcopy(sections)

        for _, entries in applicable:
            for entry in entries:
                # Only snapshot the sections this entry can touch: deep-copying the whole
                # input file per entry would scale with (file size x migration count), which
                # is costly for the large node/element sections no migration touches.
                roots = entry_root_keys(entry)
                before = {
                    key: copy.deepcopy(working[key]) for key in roots if key in working
                }

                OPERATIONS[entry["type"]](working, entry)

                after = {key: working[key] for key in roots if key in working}
                if before != after:
                    report.applied.append(entry["description"])

        # Never move backwards: the file may already be newer than the requested/known target.
        if from_version is not None and from_version > effective_to_version:
            effective_to_version = from_version
            report.to_version = effective_to_version

        working["input_version"] = _version_string(effective_to_version)

        # Commit atomically, preserving the caller's dict identity.
        sections.clear()
        sections.update(working)

    return report


def migrate_file(
    input_path: Path,
    output_path: Path,
    migrations_dir: Path | None = None,
    to_version: str | int | None = None,
) -> MigrationReport:
    """Migrate a 4C input file on disk to a newer input file version.

    Args:
        input_path: Path to the input file to migrate
        output_path: Path to write the migrated input file to (may be the same as
            `input_path` to migrate in place)
        migrations_dir: Directory containing `<version>.yaml` migration files; defaults to
            the migration database bundled with FourCIPP
        to_version: Version to migrate to (inclusive), as a version string or number;
            defaults to the newest known version. A version newer than the newest known
            migration is clamped to the latter.

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


def diff_migration(
    input_path: Path,
    migrations_dir: Path | None = None,
    to_version: str | int | None = None,
) -> tuple[MigrationReport, str]:
    """Migrate a 4C input file in memory and return a diff, without writing
    anything.

    The diff is *semantic*, not textual: both sides are written through the same YAML
    round-trip `migrate_file` uses, so it shows only what the migration changes. Formatting
    differences that a real migration would also introduce (dropped comments, added quotes,
    flow style) are deliberately excluded, as they would otherwise bury the actual changes.

    Args:
        input_path: Path to the input file to migrate
        migrations_dir: Directory containing `<version>.yaml` migration files; defaults to
            the migration database bundled with FourCIPP
        to_version: Version to migrate to (inclusive), as a version string or number;
            defaults to the newest known version. A version newer than the newest known
            migration is clamped to the latter.

    Returns:
        A report of the applied migrations, and the unified diff of the migration as a
        string, which is empty if the migration would not change the file

    Raises:
        MigrationError: If a migration entry cannot be applied, see the individual operation
            handlers in `fourcipp.migration.operations`
    """
    database = load_migration_database(migrations_dir or DEFAULT_MIGRATIONS_DIR)
    sections = load_yaml(input_path)

    with tempfile.TemporaryDirectory() as tmp_dir:
        before_path = pathlib.Path(tmp_dir) / "before.yaml"
        after_path = pathlib.Path(tmp_dir) / "after.yaml"

        # Normalize the 'before' side through the same round-trip, so the diff is free of
        # pure formatting noise.
        dump_yaml(sections, before_path)

        report = migrate_sections(
            sections,
            database,
            parse_version(to_version) if to_version is not None else None,
        )

        dump_yaml(sections, after_path)

        name = pathlib.Path(input_path).name
        diff = "".join(
            difflib.unified_diff(
                before_path.read_text(encoding="utf-8").splitlines(keepends=True),
                after_path.read_text(encoding="utf-8").splitlines(keepends=True),
                fromfile=f"{name} (before)",
                tofile=f"{name} (after)",
            )
        )

    return report, diff
