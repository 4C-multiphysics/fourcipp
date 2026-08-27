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
``OPERATIONS`` registry.
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

    Optionally restricted to specific problem types via `restrict_to_problemtypes`: the
    section is only added if the input file's `PROBLEMTYPE` (in section `PROBLEM TYPE`) is
    listed there. If `restrict_to_problemtypes` is empty/absent, or the input file does not
    specify a problem type, the section is always added (subject to the usual
    already-present check).

    See `fourcipp.utils.dict_utils.make_default_explicit`.

    Args:
        sections: Nested data dict
        entry: Migration entry with `path` and `value` fields, and an optional
            `restrict_to_problemtypes` field (list of problem type names)
    """
    restrict_to_problemtypes = entry.get("restrict_to_problemtypes")
    if restrict_to_problemtypes:
        current_problemtype = _single_match(sections, ["PROBLEM TYPE", "PROBLEMTYPE"])
        if (
            current_problemtype
            and current_problemtype[0] not in restrict_to_problemtypes
        ):
            return

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


OPERATIONS: dict[str, Callable[[dict, dict], None]] = {
    "parameter_removed": _parameter_removed,
    "parameter_renamed": _parameter_renamed,
    "parameter_default_changed": _parameter_default_changed,
    "parameter_added": _parameter_added,
    "section_renamed": _section_renamed,
    "section_merged": _section_merged,
    "parameter_value_renamed": _parameter_value_renamed,
    "parameter_moved": _parameter_moved,
    "type_renamed": _type_renamed,
    "section_added": _section_added,
}
# Registry mapping a migration entry's `type` to its handler.
