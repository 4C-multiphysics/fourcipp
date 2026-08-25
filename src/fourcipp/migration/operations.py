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
"""Operation handlers applying a single migration entry to a section dict.

Every handler has the signature ``(sections: dict, entry: dict) -> None`` and mutates
``sections`` in place. Handlers are looked up by the entry's ``type`` field via the
``OPERATIONS`` registry. The ``removed_no_replacement`` type is intentionally not part of
this registry, since it must never mutate data (see `fourcipp.migration.migrator`).
"""

from collections.abc import Callable, Sequence
from typing import Any

from fourcipp.migration.errors import MigrationError
from fourcipp.utils.dict_utils import (
    change_default,
    get_entry,
    make_default_explicit,
    remove,
    rename_parameter,
    transform_value,
)


def _get_or_create_dict(root: dict, path: Sequence[str]) -> dict:
    """Walk a path of dict keys, creating empty dicts for missing intermediate
    entries.

    Unlike the fan-out aware helpers in `fourcipp.utils.dict_utils`, this helper does not
    support lists along the path; it is only meant for locating/creating a single target
    section or parameter container.

    Args:
        root: Nested data dict to walk/create into
        path: List of keys describing the target location

    Returns:
        The dict found or created at the end of `path`

    Raises:
        MigrationError: If an existing, non-dict value blocks the path
    """
    current = root
    for key in path:
        if key not in current:
            current[key] = {}
        if not isinstance(current[key], dict):
            raise MigrationError(
                f"Cannot merge/move into '{key}': expected a dict, got "
                f"{type(current[key]).__name__}."
            )
        current = current[key]
    return current


def _single_match(sections: dict, path: Sequence[str]) -> list[Any]:
    """Resolve a path to at most one match, rejecting ambiguous fan-out.

    Args:
        sections: Nested data dict
        path: List of keys to the entry

    Returns:
        A list with the single matching value, or an empty list if `path` does not exist

    Raises:
        MigrationError: If `path` matches more than one entry
    """
    matches = list(get_entry(sections, path, optional=True))
    if len(matches) > 1:
        raise MigrationError(
            f"Path {list(path)} matched {len(matches)} entries, but only a single match "
            "is supported for this migration type."
        )
    return matches


def _apply_offset(value: Any, offset: int | float) -> Any:
    """Add an offset to an int/float value or elementwise to a list of such
    values.

    Args:
        value: Value (or list of values) to offset
        offset: Offset to add

    Returns:
        The offset value (or list of offset values)
    """
    if isinstance(value, list):
        return [_apply_offset(item, offset) for item in value]
    return value + offset


def _parameter_removed(sections: dict, entry: dict) -> None:
    """Remove a parameter, see `fourcipp.utils.dict_utils.remove`.

    Args:
        sections: Nested data dict
        entry: Migration entry with a `path` field
    """
    remove(sections, entry["path"])


def _parameter_renamed(sections: dict, entry: dict) -> None:
    """Rename a parameter, see `fourcipp.utils.dict_utils.rename_parameter`.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path` and `new_name` fields
    """
    rename_parameter(sections, entry["path"], entry["new_name"])


def _parameter_default_changed(sections: dict, entry: dict) -> None:
    """Change a parameter's default, see
    `fourcipp.utils.dict_utils.change_default`.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path`, `old_default` and `new_default` fields
    """
    change_default(sections, entry["path"], entry["old_default"], entry["new_default"])


def _parameter_added(sections: dict, entry: dict) -> None:
    """Add a new, previously unsupported parameter if its parent context
    exists.

    See `fourcipp.utils.dict_utils.make_default_explicit`.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path` and `value` fields
    """
    make_default_explicit(sections, entry["path"], entry["value"])


def _section_renamed(sections: dict, entry: dict) -> None:
    """Rename a section or a material/element/condition type discriminator.

    This is the same underlying operation as `_parameter_renamed` and `_type_renamed`, only
    the shape of `path` differs.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path` and `new_name` fields
    """
    rename_parameter(sections, entry["path"], entry["new_name"])


def _type_renamed(sections: dict, entry: dict) -> None:
    """Rename a material/element/condition type discriminator key.

    See `_section_renamed` for details, this is the same underlying operation.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path` and `new_name` fields
    """
    rename_parameter(sections, entry["path"], entry["new_name"])


def _section_added(sections: dict, entry: dict) -> None:
    """Add a new, mandatory section if it is not already present.

    See `fourcipp.utils.dict_utils.make_default_explicit`.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path` and `value` fields
    """
    make_default_explicit(sections, entry["path"], entry["value"])


def _section_merged(sections: dict, entry: dict) -> None:
    """Merge one section's parameters into another, already existing or new,
    section.

    Args:
        sections: Nested data dict
        entry: Migration entry with `old_path` and `new_path` fields

    Raises:
        MigrationError: If the entry at `old_path` is not a dict, or a key collides with an
            existing key in the target section
    """
    matches = _single_match(sections, entry["old_path"])
    if not matches:
        return

    old_value = matches[0]
    if not isinstance(old_value, dict):
        raise MigrationError(
            f"section_merged expects a dict value at {entry['old_path']}, got "
            f"{type(old_value).__name__}."
        )

    target = _get_or_create_dict(sections, entry["new_path"])
    for key, value in old_value.items():
        if key in target:
            raise MigrationError(
                f"Key '{key}' already exists in target section {entry['new_path']}, cannot "
                "merge without overwriting."
            )
        target[key] = value

    remove(sections, entry["old_path"])


def _parameter_moved(sections: dict, entry: dict) -> None:
    """Move a single parameter to a different location.

    Args:
        sections: Nested data dict
        entry: Migration entry with `old_path` and `new_path` fields

    Raises:
        MigrationError: If the target parameter already exists
    """
    matches = _single_match(sections, entry["old_path"])
    if not matches:
        return

    new_path = entry["new_path"]
    parent = _get_or_create_dict(sections, new_path[:-1])
    if new_path[-1] in parent:
        raise MigrationError(
            f"Target parameter {new_path} already exists, cannot move without overwriting."
        )
    parent[new_path[-1]] = matches[0]

    remove(sections, entry["old_path"])


def _parameter_value_renamed(sections: dict, entry: dict) -> None:
    """Remap an enum-like parameter value, leaving unmapped values untouched.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path` and `value_map` fields
    """
    value_map = entry["value_map"]
    transform_value(sections, entry["path"], lambda value: value_map.get(value, value))


def _parameter_rescaled(sections: dict, entry: dict) -> None:
    """Rescale a numeric parameter value, e.g. for a unit change.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path` and `factor` fields, and an optional `offset` field
    """
    factor = entry["factor"]
    offset = entry.get("offset", 0)
    transform_value(sections, entry["path"], lambda value: value * factor + offset)


def _reindexed(sections: dict, entry: dict) -> None:
    """Offset an index or a list of indices, e.g. to change a 0-based to
    1-based convention.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path` and `offset` fields
    """
    offset = entry["offset"]
    transform_value(sections, entry["path"], lambda value: _apply_offset(value, offset))


def _parameters_merged(sections: dict, entry: dict) -> None:
    """Merge multiple parameters into a single new one using a named transform.

    All `old_paths` must resolve to exactly one match each; if any of them is missing, this
    is treated as a no-op (e.g. the file was already migrated, or partially authored by hand).

    Args:
        sections: Nested data dict
        entry: Migration entry with `old_paths`, `new_path` and `transform` fields

    Raises:
        MigrationError: If any `old_paths` entry matches more than one value, or `transform`
            is not a known transform name
    """
    if entry["transform"] not in TRANSFORMS:
        raise MigrationError(f"Unknown transform '{entry['transform']}'.")
    transform = TRANSFORMS[entry["transform"]]

    old_paths = entry["old_paths"]
    values = []
    for old_path in old_paths:
        matches = _single_match(sections, old_path)
        if not matches:
            return
        values.append(matches[0])

    new_path = entry["new_path"]
    parent = _get_or_create_dict(sections, new_path[:-1])
    parent[new_path[-1]] = transform(values)

    for old_path in old_paths:
        remove(sections, old_path)


TRANSFORMS: dict[str, Callable[[list[Any]], Any]] = {
    "as_list": list,
}
# Named, reusable value combinators for `parameters_merged` entries.


# Registry mapping a migration entry's `type` to its handler. `removed_no_replacement` is
# deliberately not part of this registry: it must never mutate data and is handled directly
# by `fourcipp.migration.migrator.migrate_sections`.
OPERATIONS: dict[str, Callable[[dict, dict], None]] = {
    "parameter_removed": _parameter_removed,
    "parameter_renamed": _parameter_renamed,
    "parameter_default_changed": _parameter_default_changed,
    "parameter_added": _parameter_added,
    "section_renamed": _section_renamed,
    "section_merged": _section_merged,
    "parameter_value_renamed": _parameter_value_renamed,
    "parameter_moved": _parameter_moved,
    "parameter_rescaled": _parameter_rescaled,
    "parameters_merged": _parameters_merged,
    "type_renamed": _type_renamed,
    "reindexed": _reindexed,
    "section_added": _section_added,
}
