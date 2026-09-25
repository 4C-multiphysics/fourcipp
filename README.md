<p align="center">
  <picture>
    <source
      srcset="https://raw.githubusercontent.com/4C-multiphysics/fourcipp/refs/heads/main/docs/assets/fourcipp_logo_white.svg"
      media="(prefers-color-scheme: dark)">
    <img
      src="https://raw.githubusercontent.com/4C-multiphysics/fourcipp/refs/heads/main/docs/assets/fourcipp_logo_black.svg"
      width="300"
      title="FourCIPP"
      alt="FourCIPP logo">
  </picture>
</p>

FourCIPP (**FourC** **I**nput **P**ython **P**arser) holds a Python Parser to simply interact with [4C](https://github.com/4C-multiphysics/4C) YAML input files. This tool provides a streamlined approach to data handling for third party tools.

## Overview <!-- omit from toc -->
- [Installation](#installation)
  - [Python Environment](#python-environment)
  - [Installation from PyPI](#installation-from-pypi)
  - [Installation from Github (most recent version)](#installation-from-github-most-recent-version)
  - [Installation from source](#installation-from-source)
- [Quickstart example](#quickstart-example)
- [Configuration](#configuration)
- [Migrating input files](#migrating-input-files)
- [Developing FourCIPP](#developing-fourcipp)
- [Dependency Management](#dependency-management)
- [License](#license)

## Installation

### Python Environment

FourCIPP is a Python project supporting Python versions 3.10 - 3.13. To use FourCIPP it is recommended to install it into a virtual Python environment such as [Conda](https://anaconda.org/anaconda/conda)/[Miniforge](https://conda-forge.org/download/) or [venv](https://docs.python.org/3/library/venv.html).

An exemplary [Conda](https://anaconda.org/anaconda/conda)/[Miniforge](https://conda-forge.org/download/) environment can be created and loaded with

```bash
# Create the environment (this only has to be done once)
conda create -n fourcipp python=3.13
# Activate the environment
conda activate fourcipp
```

To now install FourCIPP different ways exist.

### Installation from PyPI

FourCIPP is published on [PyPI](https://pypi.org/project/FourCIPP/) as a universal wheel, meaning you can install it on Windows, Linux and macOS with:

```bash
pip install fourcipp
```

or a specific version with:

```bash
pip install fourcipp==0.28.0
```

### Installation from Github (most recent version)

Additionally, the latest `main` version of FourCIPP can be installed directly from Github via:

```bash
pip install git+https://github.com/4C-multiphysics/fourcipp.git@main
```

### Installation from source

If you intend on developing FourCIPP it is crucial to install FourCIPP from source, i.e., cloning the repository from Github. You can then either install it in a non-editable or editable fashion.

- Install all requirements without fixed versions in a non-editable fashion via:

  ```bash
  # located at the root of the repository
  pip install .
  ```

  and without fixed versions in an editable fashion via:

  ```bash
  # located at the root of the repository
  pip install -e .
  ```

  > Note: This is the default behavior. This allows to use fourcipp within other projects without version conflicts.

- Alternatively, you can install all requirements with fixed versions in a non-editable fashion with:

  ```bash
  pip install .[safe]
  ```

  and with fixed versions in an editable fashion via:

  ```bash
  # located at the root of the repository
  pip install -e .[safe]
  ```

Once installed, FourCIPP is ready to be used 🎉

## Quickstart example
<!--example, do not remove this comment-->
```python
from fourcipp.fourc_input import FourCInput

# Create a new 4C input via
input_4C = FourCInput()

# Or load an existing input file
input_4C = FourCInput.from_4C_yaml(input_file_path)

# Add or overwrite sections
input_4C["PROBLEM TYPE"] = {"PROBLEMTYPE": "Structure"}
input_4C["PROBLEM SIZE"] = {"DIM": 3, "ELEMENTS": 1_000}

# Update section parameter
input_4C["PROBLEM SIZE"]["ELEMENTS"] = 1_000_000

# Add new parameter
input_4C["PROBLEM SIZE"]["NODES"] = 10_000_000

# Remove section
removed_section = input_4C.pop("PROBLEM SIZE")

# Dump to file
input_4C.dump(input_file_path, validate=True)
```
<!--example, do not remove this comment-->

## Configuration
FourCIPP utilizes the `4C_metadata.yaml` and `schema.json` files generated during the 4C build to remain up-to-date with your 4C build. By default, the files for the latest 4C input version can be found in `src/fourcipp/config`. You can add custom metadata and schema paths to the configuration file `src/fourcipp/config/config.yaml` by adding a new profile:
```yaml
profile: your_custom_files
profiles:
  your_custom_files:
    4C_metadata_path: /absolute/path/to/your/4C_metadata.yaml
    json_schema_path: /absolute/path/to/your/4C_schema.json
  default:
    4C_metadata_path: 4C_metadata.yaml
    json_schema_path: 4C_schema.json
    description: 4C metadata from the latest successful nightly 4C build
  4C_docker_main:
    4C_metadata_path: /home/user/4C/build/4C_metadata.yaml
    json_schema_path: /home/user/4C/build/4C_schema.json
    description: 4C metadata in the main 4C docker image
```
and select it using the `profile` entry.


## Migrating input files
4C input files carry an optional `input_version` field. Using it, and migrating input files
across versions, is entirely optional: 4C never requires `input_version` to be set or kept
up to date, it only warns on a mismatch.

FourCIPP ships an optional migration tool that applies a versioned database of known,
mechanical input file changes (parameter/section renames, removals, default changes, etc.),
bundled under `src/fourcipp/migration/migrations/` (see the `README.md` there for the full
schema). Run it via:
```commandline
fourcipp migrate path/to/input.4C.yaml
```
By default, since the migrated file is the one compatible with the current 4C version, it
replaces the input file at its original path, while the pre-migration file is kept alongside
as a backup, tagged with the input file version it was on before the migration, e.g.
`_v00000.4C.yaml` (no backup is created if no migration was actually
necessary); use `-o`/`--overwrite` to migrate in place without keeping that backup. Use
`--to-version` to migrate to a specific input file version instead of the newest known one,
and `--migrations-dir` to use a custom migration database, e.g. one vendored from a specific
4C version. The command always prints a short one-line summary, e.g.:
```commandline
File 'input.4C.yaml' migrated: 2 migrations applied, pre-migration file saved as 'input_v00000.4C.yaml'.
```
To preview a migration without changing anything, use `--dry-run`, which prints a unified
diff and writes no file:
```commandline
fourcipp migrate path/to/input.4C.yaml --dry-run > migration.diff
```
The diff is *semantic*: both sides are written through the same YAML round-trip, so it shows
only what the migration actually changes, not formatting differences (dropped comments,
added quotes) that any rewrite of the file would introduce anyway. `--dry-run` also doubles
as a validation mode, reporting migrations that cannot be applied without touching the file.

Changes that cannot be applied automatically (e.g. a
feature removed without a replacement) are never silently dropped; they are reported so they
can be resolved by hand.


## Developing FourCIPP

If you plan on actively developing FourCIPP it is advisable to install in editable mode with the additional developer requirements like

```bash
pip install -e .[dev]
```

> Note: The developer requirements can also be installed in non-editable installs. Finally, you can install the pre-commit hook with:

```bash
pre-commit install
```

## Dependency Management

To ease the dependency update process [`pip-tools`](https://github.com/jazzband/pip-tools) is utilized. To create the necessary [`requirements.txt`](./requirements.txt) file simply execute

```
pip-compile --all-extras --output-file=requirements.txt requirements.in
````

To upgrade the dependencies simply execute

```
pip-compile --all-extras --output-file=requirements.txt --upgrade requirements.in
````

## License

This project is licensed under a MIT license. For further information check [`LICENSE`](./LICENSE).
