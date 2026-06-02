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
"""Validation utils."""

from __future__ import annotations

import sys
from collections.abc import Iterable, Sequence

import jsonschema_rs

from fourcipp.utils.yaml_io import dict_to_yaml_string

MAX_INT = 2_147_483_647  # C++ value
MAX_FLOAT = sys.float_info.max


class ValidationError(Exception):
    """FourCIPP validation error."""

    @staticmethod
    def path_indexer(path: Sequence[str | int]) -> str:
        """Create a path representation to walk the dict."""
        path_for_data = ""
        for p in path:
            if isinstance(p, str):
                p = '"' + p + '"'
            path_for_data += "[" + str(p) + "]"
        return path_for_data

    @staticmethod
    def indent(text: str, n_spaces: int = 4) -> str:
        """Indent the text."""
        indent_with_newline = "\n" + " " * n_spaces
        return indent_with_newline + text.replace("\n", indent_with_newline)

    @classmethod
    def from_schema_validation_errors(
        cls, errors: Iterable[jsonschema_rs.ValidationError]
    ) -> ValidationError:
        """Create error from multiple errors.

        Args:
            errors: Errors to raise

        Returns:
            New error for this case
        """
        message = "\nValidation failed, due to the following parameters:"

        for error in errors:
            message += "\n\n- Parameter in " + cls.path_indexer(error.instance_path)
            message += cls.indent(cls.indent(dict_to_yaml_string(error.instance), 4))
            message += cls.indent("Error: " + error.message, 2)

        return cls(message)

    @classmethod
    def from_overflow_errors(
        cls, object_paths_with_errors: Iterable[tuple[list[str | int], int | float]]
    ) -> ValidationError:
        """Create error from multiple errors.

        Args:
            errors: Errors to raise

        Returns:
            New error for this case
        """
        message = "\nValidation failed, due to the following parameters:"

        for path, obj in object_paths_with_errors:
            message += "\n\n- Parameter in " + cls.path_indexer(path)
            message += cls.indent(cls.indent(str(obj), 4))

            if isinstance(obj, int):
                error = f"Maximum int value {MAX_INT} exceeded"
            else:
                error = f"Maximum float value {MAX_FLOAT} exceeded"
            message += cls.indent("Error: " + error, 2)

        return cls(message)


def find_keys_exceeding_max_value(
    obj: object, path_for_data: list[str | int] | None = None
) -> Iterable[tuple[list[str | int], int | float]]:
    """Find entries exceeding max values.

    Args:
        obj (object): Object to check
        path_for_data: Path to the data

    Yields:
        path for each case where this problem emerges
    """
    if path_for_data is None:
        path_for_data = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from find_keys_exceeding_max_value(value, path_for_data + [key])
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            yield from find_keys_exceeding_max_value(item, path_for_data + [index])
    elif isinstance(obj, int) and abs(obj) > MAX_INT:
        yield path_for_data, obj
    elif isinstance(obj, float) and abs(obj) > MAX_FLOAT:
        yield path_for_data, obj


def validate_using_json_schema(
    data: dict,
    validator: jsonschema_rs.Validator,
) -> bool:
    """Validate data using a JSON schema.

    Args:
        data: Data to validate
        validator: Validator for validation

    Returns:
        True if successful
    """

    try:
        validator.validate(data)
    except jsonschema_rs.ValidationError as exception:
        # Validation failed, look for all errors
        raise ValidationError.from_schema_validation_errors(
            validator.iter_errors(data)
        ) from exception
    except ValueError as exception:
        if str(exception).endswith("too big to convert"):
            raise ValidationError.from_overflow_errors(
                find_keys_exceeding_max_value(data)
            ) from exception
        raise
    return True
