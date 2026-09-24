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
"""CLI utils."""

import argparse
import pathlib
import shutil
import sys
import tempfile

from loguru import logger

from fourcipp import CONFIG
from fourcipp.fourc_input import FourCInput
from fourcipp.migration.database import format_version
from fourcipp.migration.migrator import (
    IMPLICIT_INPUT_VERSION,
    diff_migration,
    migrate_file,
)
from fourcipp.utils.configuration import (
    change_profile,
    show_config,
)
from fourcipp.utils.type_hinting import Path
from fourcipp.utils.yaml_io import dump_yaml, load_yaml


def modify_input_with_defaults(
    input_path: Path, overwrite: bool
) -> None:  # pragma: no cover
    """Apply user defaults to an input file located at input_path.

    Args:
         input_path: Input filename to apply user defaults to.
         overwrite: Whether to overwrite the existing input file.
                         By default, a new file with suffix '_mod.4C.yaml' is created.
    """
    output_appendix = "_mod"

    input_path = pathlib.Path(input_path)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file '{input_path}' does not exist.")
    input_data = FourCInput.from_4C_yaml(input_path)
    user_defaults_string = CONFIG.user_defaults_path
    input_data.apply_user_defaults(user_defaults_string)
    if overwrite:
        output_filename = input_path
    else:
        names = input_path.name.split(".")
        names[0] += output_appendix
        output_filename = input_path.parent / ".".join(names)
    input_data.dump(output_filename)
    logger.info(f"Input file incl. user defaults is now '{output_filename}'.")


def format_file(
    input_file: str, sort_sections: bool = False
) -> None:  # pragma: no cover
    """Formatting file.

    Args:
        input_file: File to format
        sort_sections: Sort sections
    """
    if sort_sections:
        # Requires reading the config
        fourc_input = FourCInput.from_4C_yaml(input_file)
        fourc_input.dump(input_file, use_fourcipp_yaml_style=True)
    else:
        # No config required, is purely a style question
        dump_yaml(load_yaml(input_file), input_file, use_fourcipp_yaml_style=True)


def migrate_input_file(
    input_file: str,
    overwrite: bool,
    to_version: str | None = None,
    migrations_dir: str | None = None,
    dry_run: bool = False,
) -> None:  # pragma: no cover
    """Migrate an input file to a newer input file version.

    Since the migrated file is the one that is actually compatible with the current 4C
    version, by default it replaces the input file at its original path, while the
    pre-migration file is kept alongside as a backup, tagged with the version it was on
    before the migration, e.g. '_v1.0.0.4C.yaml'. Input files without an `input_version`
    field are assumed to be on version `IMPLICIT_INPUT_VERSION`. No backup is created if no
    migration was actually necessary.

    Args:
        input_file: Input filename to migrate
        overwrite: Whether to migrate the input file in place, without keeping a backup of
                        the pre-migration file.
        to_version: Version to migrate to (inclusive); defaults to the newest known version.
            A version newer than the newest known migration is clamped to the latter.
        migrations_dir: Directory containing `<version>.yaml` migration files; defaults to
                             the migration database bundled with FourCIPP
        dry_run: Whether to only print the diff the migration would produce, without
                      writing anything
    """
    input_path = pathlib.Path(input_file)
    if not input_path.is_file():
        raise FileNotFoundError(f"Input file '{input_path}' does not exist.")

    if dry_run:
        report, diff = diff_migration(input_path, migrations_dir, to_version)
        logger.info(str(report))

        if report.clamp_warning is not None:
            print(f"Warning: {report.clamp_warning}")

        if diff:
            print(diff, end="" if diff.endswith("\n") else "\n")

        n_applied = len(report.applied)
        plural = "" if n_applied == 1 else "s"
        print(
            f"Dry run for '{input_path}': {n_applied} migration{plural} would be applied, "
            "no file was written."
        )
        return

    # Migrate into a staging file first, so whether any migration was actually necessary is
    # known before deciding whether to keep a backup of the pre-migration file.
    with tempfile.TemporaryDirectory() as tmp_dir:
        staged_path = pathlib.Path(tmp_dir) / input_path.name
        report = migrate_file(input_path, staged_path, migrations_dir, to_version)
        logger.info(str(report))

        if report.clamp_warning is not None:
            print(f"Warning: {report.clamp_warning}")

        if not report.changed:
            shutil.copyfile(staged_path, input_path)
            print(f"File '{input_path}' migrated: no changes necessary.")
            print(f"Updated the version number in input file.")
            return

        n_applied = len(report.applied)
        plural = "" if n_applied == 1 else "s"

        if overwrite:
            shutil.copyfile(staged_path, input_path)
            print(
                f"File '{input_path}' migrated: {n_applied} migration{plural} applied, "
                "file overwritten in place."
            )
            return

        # Tag the backup with the version the file was on before the migration.
        original_version = (
            report.from_version
            if report.from_version is not None
            else IMPLICIT_INPUT_VERSION
        )
        backup_appendix = f"_v{format_version(original_version)}"

        names = input_path.name.split(".")
        names[0] += backup_appendix
        backup_path = input_path.parent / ".".join(names)
        input_path.rename(backup_path)
        shutil.copyfile(staged_path, input_path)
        print(
            f"File '{input_path}' migrated: {n_applied} migration{plural} applied, "
            f"pre-migration file saved as '{backup_path}'."
        )


def main() -> None:
    """Main CLI interface."""
    # Configure logger based on CLI args and configuration.
    # First all existing loggers are removed
    # and enabled only when logging is requested (see below).
    logger.remove()

    # The FourCIPP CLI is build upon argparse and subparsers. The latter ones are use to interface
    # mutual exclusive commands. If you add a new command add a new subparser and add the CLI
    # parameters as you would normally with argparse. Finally add the new command to the pattern
    # matching. More details can be found here:
    # https://docs.python.org/3/library/argparse/html#sub-commands

    main_parser = argparse.ArgumentParser(prog="FourCIPP")
    subparsers = main_parser.add_subparsers(dest="command")

    # Config parser
    subparsers.add_parser("show-config", help="Show the FourCIPP config.")

    # Switch config parser
    switch_config_profile_parser = subparsers.add_parser(
        "switch-config-profile", help="Switch user config profile."
    )
    switch_config_profile_parser.add_argument(
        "profile",
        help=f"FourCIPP config profile name.",
        type=str,
    )

    # Apply user defaults parser
    apply_user_defaults_parser = subparsers.add_parser(
        "apply-user-defaults",
        help="Apply user defaults from the file given in the user defaults path.",
    )

    apply_user_defaults_parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help=f"Overwrite existing input file.",
    )

    apply_user_defaults_parser.add_argument(
        "input-file",
        help=f"4C input file.",
        type=str,
    )

    # Format parser
    format_parser = subparsers.add_parser(
        "format",
        help="Format the file in fourcipp style. This sorts the sections and uses the flow styles from FourCIPP",
    )

    format_parser.add_argument(
        "input-file",
        help=f"4C input file.",
        type=str,
    )

    format_parser.add_argument(
        "--sort-sections",
        action="store_true",
        help=f"Overwrite existing input file.",
    )

    # Migrate parser
    migrate_parser = subparsers.add_parser(
        "migrate",
        help="Migrate an input file to a newer input file version. This is entirely "
        "optional, 4C never requires the input_version field to be set or up to date.",
    )

    migrate_parser.add_argument(
        "input-file",
        help=f"4C input file.",
        type=str,
    )

    migrate_parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Migrate the input file in place, without keeping a backup of the "
        "pre-migration file. By default, the input file is replaced with the migrated "
        "version, and the pre-migration file is kept alongside, tagged with the version it "
        "was on before the migration, e.g. '_v1.0.0.4C.yaml'.",
    )

    migrate_parser.add_argument(
        "--to-version",
        help="Input file version to migrate to. Defaults to the newest known version.",
        type=str,
        default=None,
    )

    migrate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the unified diff the migration would produce and exit, without "
        "writing or changing any file. The diff is semantic: both sides are written "
        "through the same YAML round-trip, so it shows only what the migration changes, "
        "not formatting differences such as dropped comments.",
    )

    migrate_parser.add_argument(
        "--migrations-dir",
        help="Directory containing the migration database. Defaults to the migration "
        "database bundled with FourCIPP.",
        type=str,
        default=None,
    )
    # Add global CLI logging options
    main_parser.add_argument(
        "--log-file",
        help="Path to log file. If set, enables logging to this file.",
        type=str,
        default=None,
    )
    main_parser.add_argument(
        "--log-screen",
        help="Enable logging to screen (stdout).",
        action="store_true",
    )

    # Parse args and build kwargs for commands. Skip log-related global args.
    parsed_args = main_parser.parse_args(sys.argv[1:])

    # Determine whether logging should be enabled. --log-file and --log-screen are
    # independent: either, both, or neither may be given.
    try:
        log_file_arg = getattr(parsed_args, "log_file", None)
        log_screen_arg = getattr(parsed_args, "log_screen", False)
        if log_file_arg or log_screen_arg:
            logger.enable("fourcipp")
            if log_file_arg:
                target = pathlib.Path(log_file_arg)
                logger.add(
                    target.as_posix(), mode="w", format="{time} {level} {message}"
                )
                logger.debug(f"Logging enabled to file: {target}")
            if log_screen_arg:
                logger.add(sys.stdout, format="{message}")
                logger.debug("Logging enabled to stdout")
        else:
            # Keep package logging disabled
            logger.disable("fourcipp")
    except Exception:
        logger.debug("Could not set up logging; continuing without logging.")
        logger.disable("fourcipp")

    kwargs: dict = {}
    for key, value in vars(parsed_args).items():
        if key in ("log_file", "log_screen"):
            continue
        kwargs[key.replace("-", "_")] = value
    command = kwargs.pop("command")

    # Select the desired command
    match command:
        case "show-config":
            show_config()
        case "switch-config-profile":
            change_profile(**kwargs)
        case "apply-user-defaults":
            input_path = pathlib.Path(kwargs.pop("input_file"))
            overwrite = kwargs.pop("overwrite")
            modify_input_with_defaults(input_path, overwrite)
        case "format":
            format_file(**kwargs)
        case "migrate":
            migrate_input_file(**kwargs)
