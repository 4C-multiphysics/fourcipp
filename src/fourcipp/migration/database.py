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
(without extension) is the version the file upgrades *to*, e.g. `1.1.0.yaml` contains the
changes needed to go from the previous version to `1.1.0`.
"""

import re
from pathlib import Path as PathlibPath

from fourcipp.migration.errors import MigrationError
from fourcipp.migration.operations import OPERATIONS
from fourcipp.utils.type_hinting import Path
from fourcipp.utils.yaml_io import load_yaml

Version = tuple[int, int, int]

# All migration entry types known to the tool.
KNOWN_TYPES = set(OPERATIONS) | {"removed_no_replacement"}

# Fields required on every migration entry, regardless of its type.
_UNIVERSAL_FIELDS = {"id", "type", "description"}

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
    "parameter_rescaled": {"path", "factor"},
    "parameters_merged": {"old_paths", "new_path", "transform"},
    "type_renamed": {"path", "new_name"},
    "reindexed": {"path", "offset"},
    "section_added": {"path", "value"},
    "removed_no_replacement": {"path", "message"},
}

_VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def parse_version(version_string: str) -> Version:
    """Parse a `MAJOR.MINOR.PATCH` version string.

    Args:
        version_string: Version string to parse

    Returns:
        The version as a `(major, minor, patch)` tuple of ints

    Raises:
        MigrationError: If `version_string` is not a valid `MAJOR.MINOR.PATCH` version
    """
    match = _VERSION_PATTERN.fullmatch(version_string.strip())
    if match is None:
        raise MigrationError(
            f"'{version_string}' is not a valid MAJOR.MINOR.PATCH version string."
        )
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def validate_entry(entry: dict) -> None:
    """Validate a single migration entry.

    Args:
        entry: Migration entry to validate

    Raises:
        MigrationError: If a universal or type-specific required field is missing, or the
            entry's `type` is unknown
    """
    missing_universal = _UNIVERSAL_FIELDS - set(entry)
    if missing_universal:
        raise MigrationError(
            f"Migration entry {entry} is missing required field(s): {missing_universal}."
        )

    entry_type = entry["type"]
    if entry_type not in KNOWN_TYPES:
        raise MigrationError(
            f"Migration entry '{entry['id']}' has unknown type '{entry_type}'. Known types "
            f"are: {sorted(KNOWN_TYPES)}."
        )

    missing_type_fields = _REQUIRED_FIELDS[entry_type] - set(entry)
    if missing_type_fields:
        raise MigrationError(
            f"Migration entry '{entry['id']}' of type '{entry_type}' is missing required "
            f"field(s): {missing_type_fields}."
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

    for entry in entries:
        validate_entry(entry)

    return entries


def load_migration_database(migrations_dir: Path) -> dict[Version, list[dict]]:
    """Load all migration files from a directory, keyed by the version they
    upgrade to.

    Args:
        migrations_dir: Directory containing `<version>.yaml` migration files

    Returns:
        Mapping from target version to its list of migration entries

    Raises:
        MigrationError: If a filename is not a valid version, or two files target the same
            version
    """
    database: dict[Version, list[dict]] = {}
    for path in sorted(PathlibPath(migrations_dir).glob("*.yaml")):
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
