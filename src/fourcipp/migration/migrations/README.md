# Input file migration database

This directory contains the migration database used by FourCIPP's optional input file
migration tool (`fourcipp.migration`, CLI: `fourcipp migrate`).

Using 4C's `input_version` field, and this migration database, is entirely **optional**.
Input files without `input_version` set, or that are never migrated, continue to work as
before; 4C itself only ever warns on a version mismatch, it never enforces or migrates
anything.

## Known limitations

Migration entries can only target **typed** sections (e.g. `MATERIALS`, `DESIGN ... CONDITIONS`),
whose entries are structured YAML mappings such as `{"MAT": 1, "MAT_ElastHyper": {...}}`.

4C's **legacy**, line-based sections (`NODE COORDS`, any section ending in `ELEMENTS` or
`NODE TOPOLOGY`, `PARTICLES`) store their entries as plain inline-dat strings, e.g.
`"1 SOLID QUAD4 1 2 3 4 MAT 1 KINEM nonlinear THICKNESS 1.0"`, with parameters embedded
positionally/as keyword pairs inside the string rather than as dict keys. The migration tool
cannot reach into these strings: a `path` may only target such a section as a whole (e.g. to
`parameter_removed`/`section_renamed`/`section_merged` the entire section), not an individual
keyword within an element/node/topology/particle line. Attempting to do so raises a `TypeError`
rather than silently corrupting data. Adding structured support for these sections was
deliberately not pursued, since 4C's legacy element/node input is expected to be replaced by a
different structure entirely at some point, making it not worth the effort for now.

## Layout

Each file is named `<version>.yaml`, where `<version>` is the `MAJOR.MINOR.PATCH` input file
version that its migrations upgrade *to*, e.g. `1.1.0.yaml` contains the changes needed to go
from the previous known version to version `1.1.0`. Every file contains a single top-level key:

```yaml
migrations:
  - id: <unique-slug>
    type: <migration-type>
    description: <human readable summary>
    pr: <optional PR/issue reference>
    # ... type-specific fields, see below
```

Migrations are applied strictly in ascending version/file order, and within a file in the
order they are listed.

## Common fields

- `id` (required): A unique, stable, human-readable identifier for the entry (e.g.
  `mat-elasthyper-remove-nummat`). Used in migration reports.
- `type` (required): One of the migration types below.
- `description` (required): Human-readable summary shown in migration reports.
- `pr` (optional): Reference to the pull request/issue that introduced the underlying change.

All paths (`path`, `old_path`, `new_path`, `old_paths`) are lists of string keys, walking
into the nested input file data exactly like `fourcipp.utils.dict_utils`. Since sections such
as `MATERIALS` are lists of `{"<discriminator>": id, "<TypeName>": {...}}` dicts, a path
segment naming a type (e.g. `MAT_ElastHyper`) transparently fans out over every matching list
entry - no separate scoping mechanism is required.

## Migration types

| `type`                      | Required fields                                | Notes |
|------------------------------|------------------------------------------------|-------|
| `parameter_removed`          | `path`                                          | Drops the parameter if present. |
| `parameter_renamed`          | `path`, `new_name`                              | `path`'s last element is the old name. |
| `parameter_default_changed`  | `path`, `old_default`, `new_default`             | Makes `old_default` explicit if absent; drops the parameter if it equals `new_default`. |
| `parameter_added`            | `path`, `value`                                  | Only added if the parent section/list entry already exists. |
| `section_renamed`            | `path`, `new_name`                               | Same mechanism as `parameter_renamed`, `path` is `[old_section_name]`. |
| `section_merged`             | `old_path`, `new_path`                           | Merges a dict-valued section into another (created if missing); errors on key collisions. |
| `parameter_value_renamed`    | `path`, `value_map`                              | Remaps enum-like values; unmapped values are left untouched. |
| `parameter_moved`            | `old_path`, `new_path`                           | Moves a single parameter; only a single match is supported (no fan-out on the target). |
| `parameter_rescaled`         | `path`, `factor` (optional `offset`)              | `new_value = old_value * factor + offset`, e.g. for a unit change. |
| `parameters_merged`          | `old_paths`, `new_path`, `transform`              | Combines several parameters via a named transform (currently: `as_list`). |
| `type_renamed`               | `path`, `new_name`                               | Renames a material/element/condition type discriminator; same mechanism as `parameter_renamed`. |
| `reindexed`                  | `path`, `offset`                                 | Adds `offset` to an int value, or every int in a list (e.g. 0-based to 1-based). |
| `section_added`              | `path`, `value`                                  | Adds a new, mandatory section if not already present. |
| `removed_no_replacement`     | `path`, `message`                                | Never auto-migrated. Only flags the input file for manual attention if `path` is present. |

> **Caveat:** For `parameter_moved`, `parameters_merged` and `section_merged`, the *write*
> side (`new_path`, and its parent for `parameters_merged`) must resolve to a plain nested
> dict; it cannot fan out through a list-of-dicts section such as `MATERIALS`. The *read*
> side (`old_path`/`old_paths`) has no such restriction and can target entries inside such
> lists (e.g. `["MATERIALS", "MAT_Foo", "TOL"]`), as long as it resolves to a single match.

## Examples

The following are fictitious examples (not real 4C changes) illustrating each field's
purpose. They do not need to cover every migration type; see the table above for the full
list and their required fields.

```yaml
migrations:
  # A straightforward removal, the simplest and most common type.
  - id: mat-elasthyper-remove-nummat
    type: parameter_removed
    description: "NUMMAT is redundant with the length of MATIDS and was removed."
    pr: "https://github.com/4C-multiphysics/4C/pull/12345"
    path: ["MATERIALS", "MAT_ElastHyper", "NUMMAT"]

  # Renaming a parameter: path's last element is the OLD name, new_name is the new one.
  - id: mat-foo-rename-visco
    type: parameter_renamed
    description: "VISCO was renamed to VISCOSITY for clarity."
    path: ["MATERIALS", "MAT_Foo", "VISCO"]
    new_name: "VISCOSITY"

  # A changed default: makes the OLD default explicit on files that relied on it, so their
  # behavior does not silently change; if a file already has the NEW default written out
  # explicitly, that value is left untouched (it is not equal to old_default).
  - id: mat-foo-default-density-changed
    type: parameter_default_changed
    description: "The default DENS changed from 1.0 to 0.0 to avoid silently assuming mass."
    path: ["MATERIALS", "MAT_Foo", "DENS"]
    old_default: 1.0
    new_default: 0.0

  # Renaming a section is the same mechanism as parameter_renamed, just at section level.
  - id: section-fluid-dyn-renamed
    type: section_renamed
    description: "FLUID DYNAMIC was renamed to FLUID DYNAMICS for consistency."
    path: ["FLUID DYNAMIC"]
    new_name: "FLUID DYNAMICS"

  # Renaming a type discriminator (e.g. a material's type name) uses the same mechanism,
  # only path ends in the OLD type name instead of a parameter name. A different, unrelated
  # material is used here so later examples can keep referring to MAT_Foo consistently.
  - id: mat-baz-renamed-to-qux
    type: type_renamed
    description: "MAT_Baz was renamed to MAT_Qux as part of a naming cleanup."
    path: ["MATERIALS", "MAT_Baz"]
    new_name: "MAT_Qux"

  # Merging a whole section's parameters into another (new or existing) section.
  # Errors if any key would collide with one already present at new_path.
  - id: section-contact-merged-into-mortar
    type: section_merged
    description: "CONTACT DYNAMIC was merged into MORTAR COUPLING PARAMS."
    old_path: ["CONTACT DYNAMIC"]
    new_path: ["MORTAR COUPLING PARAMS"]

  # Moving a single parameter to a different (possibly new) parent location.
  - id: mat-foo-move-tolerance-to-solver
    type: parameter_moved
    description: "TOL moved from MAT_Foo to the NONLINEAR SOLVER section."
    old_path: ["MATERIALS", "MAT_Foo", "TOL"]
    new_path: ["NONLINEAR SOLVER", "TOL"]

  # Remapping enum-like string values; any value not listed in value_map is left as-is.
  - id: mat-foo-rename-solve-values
    type: parameter_value_renamed
    description: "SOLVE options were renamed from OST/CONVOL to OneStepTheta/Convolution."
    path: ["MATERIALS", "MAT_Foo", "SOLVE"]
    value_map:
      OST: "OneStepTheta"
      CONVOL: "Convolution"

  # Rescaling a numeric value, e.g. for a unit change (new_value = old_value * factor +
  # offset). Works transparently on both a single value and a list of values.
  - id: mat-foo-density-kg-to-g
    type: parameter_rescaled
    description: "DENS is now given in g/mm^3 instead of kg/mm^3."
    path: ["MATERIALS", "MAT_Foo", "DENS"]
    factor: 1000.0

  # Combining several separate parameters into one new list-valued parameter via a named
  # transform (currently only "as_list" is available). All old_paths must exist; if any is
  # missing, the whole entry is skipped as a no-op (e.g. the file was already migrated by
  # hand). Here, three separate direction components in a plain (non-list) section are
  # combined into a single vector. Note the target must be a plain section, see the caveat
  # below the table above.
  - id: foo-dynamic-merge-direction-components
    type: parameters_merged
    description: >
      DIR_X, DIR_Y and DIR_Z were merged into a single 3-component DIRECTION vector.
    old_paths:
      - ["FOO DYNAMIC", "DIR_X"]
      - ["FOO DYNAMIC", "DIR_Y"]
      - ["FOO DYNAMIC", "DIR_Z"]
    new_path: ["FOO DYNAMIC", "DIRECTION"]
    transform: "as_list"
    # Given FOO DYNAMIC: {DIR_X: 1.0, DIR_Y: 0.0, DIR_Z: 0.0, ...}, this produces
    # FOO DYNAMIC: {DIRECTION: [1.0, 0.0, 0.0], ...} (DIR_X/DIR_Y/DIR_Z removed).

  # Offsetting an index or list of indices, e.g. to switch from a 0-based to a 1-based
  # convention.
  - id: cond-foo-reindex-onoff
    type: reindexed
    description: "FUNCT indices are now 1-based instead of 0-based."
    path: ["DESIGN SURF FOO CONDITIONS", "FUNCT"]
    offset: 1

  # Adding a new, mandatory parameter to an existing section/list entry (only where the
  # parent context already exists, e.g. only for MAT_Foo entries, not everywhere).
  - id: mat-foo-add-scaling
    type: parameter_added
    description: "A new, mandatory SCALING parameter was introduced, defaulting to 1.0."
    path: ["MATERIALS", "MAT_Foo", "SCALING"]
    value: 1.0

  # Adding a new, mandatory section if it is not already present.
  - id: section-io-monitor-added
    type: section_added
    description: "IO/MONITOR STRUCTURE DBC is now always required, defaulting to disabled."
    path: ["IO/MONITOR STRUCTURE DBC"]
    value:
      INTERVAL_STEPS: -1

  # Flags files for manual attention without touching any data; never auto-applied.
  - id: mat-foo-remove-legacy-mode
    type: removed_no_replacement
    description: "LEGACY_MODE was removed with no automatic replacement."
    path: ["MATERIALS", "MAT_Foo", "LEGACY_MODE"]
    message: >
      LEGACY_MODE was removed. Review your MAT_Foo definitions and choose an equivalent
      combination of the new STRATEGY and TOLERANCE parameters.
```
