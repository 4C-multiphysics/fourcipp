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
"""Loading and validating the migration database.

The migration database is a directory of YAML files, one per input file version, each
containing a list of migration entries under a top-level `migrations` key. The filename
(without extension) is the version the file upgrades *to*, e.g. `00002.yaml` contains the
changes needed to go from the previous version to version `00002`.
"""

import re
from pathlib import Path as PathlibPath

from loguru import logger

from fourcipp.migration.errors import MigrationError
from fourcipp.migration.operations import OPERATIONS
from fourcipp.utils.type_hinting import Path
from fourcipp.utils.yaml_io import load_yaml

Version = int

VERSION_DIGITS = 5
# Number of digits an input file version is zero-padded to. The padding keeps numeric and
# lexicographic ordering identical, so versions sort correctly whether they are compared as
# numbers or as plain text. Versions exceeding this width are not truncated, they simply
# grow beyond it.

# All migration entry types known to the tool.
KNOWN_TYPES = set(OPERATIONS)

# Fields required on every migration entry, regardless of its type.
_UNIVERSAL_FIELDS = {"type", "description"}

# Fields required per migration entry `type`, in addition to `_UNIVERSAL_FIELDS`.
_REQUIRED_FIELDS: dict[str, set[str]] = {
    "parameter_removed": {"path"},
    "parameter_renamed": {"path", "new_name"},
    "parameter_default_changed": {"path", "old_default", "new_default"},
    "parameter_added": {"path", "value"},
    "section_renamed": {"path", "new_name"},
    "section_merged": {"old_path", "new_path"},
    "parameter_value_renamed": {"path", "value_map"},
    "parameter_moved": {"old_path", "new_path"},
    "type_renamed": {"path", "new_name"},
    "section_added": {"path", "value"},
}

_VERSION_PATTERN = re.compile(r"\d+")


def parse_version(version: str | int) -> Version:
    """Parse an input file version.

    Accepts both the zero-padded form written by FourCIPP (e.g. `"00002"`) and a plain
    number, as a string or as an int. The latter matters because a hand-written, unquoted
    `input_version` is loaded from YAML as an int.

    Args:
        version: Version to parse

    Returns:
        The version as an int

    Raises:
        MigrationError: If `version` is not a non-negative whole number
    """
    if isinstance(version, bool) or not isinstance(version, (str, int)):
        raise MigrationError(
            f"'{version}' is not a valid input file version, expected a number."
        )

    if isinstance(version, int):
        if version < 0:
            raise MigrationError(
                f"'{version}' is not a valid input file version, expected a "
                "non-negative number."
            )
        return version

    if _VERSION_PATTERN.fullmatch(version.strip()) is None:
        raise MigrationError(
            f"'{version}' is not a valid input file version, expected a non-negative "
            f"number, optionally zero-padded to {VERSION_DIGITS} digits, e.g. "
            f"'{format_version(2)}'."
        )
    return int(version.strip())


def format_version(version: Version) -> str:
    """Format a version as a zero-padded version string.

    Args:
        version: Version to format

    Returns:
        The version, zero-padded to `VERSION_DIGITS` digits
    """
    return f"{version:0{VERSION_DIGITS}d}"


def validate_entry(
    entry: dict, position: int | None = None, source: Path | None = None
) -> None:
    """Validate a single migration entry.

    Args:
        entry: Migration entry to validate
        position: Optional 1-based position of the entry within its file, used to point at
            the offending entry in error messages
        source: Optional path of the file the entry was read from, used in error messages

    Raises:
        MigrationError: If a universal or type-specific required field is missing, or the
            entry's `type` is unknown
    """
    label = "Migration entry"
    if position is not None:
        label += f" {position}"
    if source is not None:
        label += f" in '{source}'"

    if not isinstance(entry, dict):
        raise MigrationError(
            f"{label} must be a mapping, got {type(entry).__name__}. Entry: {entry}"
        )

    missing_universal = _UNIVERSAL_FIELDS - set(entry)
    if missing_universal:
        raise MigrationError(
            f"{label} is missing required field(s): {sorted(missing_universal)}. "
            f"Entry: {entry}"
        )

    entry_type = entry["type"]
    if entry_type not in KNOWN_TYPES:
        raise MigrationError(
            f"{label} has unknown type '{entry_type}'. Known types are: "
            f"{sorted(KNOWN_TYPES)}. Entry: {entry}"
        )

    missing_type_fields = _REQUIRED_FIELDS[entry_type] - set(entry)
    if missing_type_fields:
        raise MigrationError(
            f"{label} of type '{entry_type}' is missing required field(s): "
            f"{sorted(missing_type_fields)}. Entry: {entry}"
        )


def load_migration_file(path: Path) -> list[dict]:
    """Load and validate all migration entries from a single migration file.

    Args:
        path: Path to the migration YAML file

    Returns:
        List of validated migration entries, in file order

    Raises:
        MigrationError: If the file does not contain a `migrations` list, or any entry fails
            validation
    """
    data = load_yaml(path)
    entries = data.get("migrations") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise MigrationError(
            f"Migration file '{path}' must contain a top-level 'migrations' list."
        )

    for position, entry in enumerate(entries, start=1):
        validate_entry(entry, position=position, source=path)

    return entries


def load_migration_database(migrations_dir: Path) -> dict[Version, list[dict]]:
    """Load all migration files from a directory, keyed by the version they
    upgrade to.

    Files whose name is not a number, e.g. `00002.yaml`, are ignored, so unrelated YAML
    files can live alongside the migration database.

    Args:
        migrations_dir: Directory containing `<version>.yaml` migration files

    Returns:
        Mapping from target version to its list of migration entries

    Raises:
        MigrationError: If `migrations_dir` does not exist, or two files target the same
            version
    """
    migration_path = PathlibPath(migrations_dir)
    if not migration_path.is_dir():
        raise MigrationError(f"Migration directory '{migrations_dir}' does not exist.")
    database: dict[Version, list[dict]] = {}
    for path in sorted(migration_path.glob("*.yaml")):
        if _VERSION_PATTERN.fullmatch(path.stem) is None:
            logger.debug(
                f"Skipping '{path.name}': not a <version>.yaml migration file."
            )
            continue

        version = parse_version(path.stem)
        if version in database:
            raise MigrationError(
                f"Multiple migration files found for version {path.stem}."
            )
        database[version] = load_migration_file(path)

    return database


def select_migrations(
    database: dict[Version, list[dict]],
    from_version: Version | None,
    to_version: Version | None = None,
) -> list[tuple[Version, list[dict]]]:
    """Select migrations to apply to go from `from_version` to `to_version`.

    The selected range is open at the lower end and closed at the upper end, i.e.
    `(from_version, to_version]`. An absent `from_version` (e.g. the input file never had
    `input_version` set) is treated as the oldest possible version, selecting every migration
    up to and including `to_version`.

    Args:
        database: Migration database, as returned by `load_migration_database`
        from_version: Version to migrate from, or `None` if unknown/unset
        to_version: Version to migrate to (inclusive); defaults to the newest known version

    Returns:
        Applicable `(version, entries)` pairs, sorted in ascending version order
    """
    if to_version is None:
        if not database:
            return []
        to_version = max(database)

    return [
        (version, entries)
        for version, entries in sorted(database.items())
        if (from_version is None or version > from_version) and version <= to_version
    ]
