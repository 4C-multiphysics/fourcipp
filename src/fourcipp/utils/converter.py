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
"""Converter to convert custom types to native Python types."""

from __future__ import annotations

from typing import Any, Callable, Type, Union

import numpy as np


class Converter:
    """Converter class to convert custom types to native Python types."""

    def __init__(self):
        self._custom_converters = {}

    def register_type(
        self,
        custom_type: Type[Any],
        converter_function: Callable[[Converter, Any], Any],
    ) -> Converter:
        """Register a custom type and its converter function.

        The first argument of the converter_function is a converter object.
        This allows you to pass self down to your converter function to
        recursively call it and use custom types you already registered.
        The second argument is the object to be converted.

        Args:
            custom_type: Custom class to register
            converter_function: Converter function
        """
        self._custom_converters[custom_type] = converter_function
        return self

    def register_types(self, types_dict: dict):
        """Register multiple custom types and their converter functions.

        Args:
            types_dict: Dictionary with custom types as keys and
            converter functions as values
        """
        self._custom_converters.update(types_dict)
        return self

    def register_numpy_types(self) -> Converter:
        """Register NumPy types and their converter functions."""

        def convert_ndarray(converter: Converter, obj: np.ndarray):
            """Convert a NumPy ndarray to a list.

            Args:
                converter: Converter object
                obj: NumPy ndarray to convert
            """
            return converter(obj.tolist())

        def convert_generic(converter: Converter, obj: np.generic):
            """Convert a NumPy generic type to a native Python type.

            Args:
                converter: Converter object
                obj: NumPy generic type to convert
            """
            return obj.item()

        self.register_type(np.generic, convert_generic)
        self.register_type(np.ndarray, convert_ndarray)
        return self

    def __call__(self, obj: Any) -> Any:
        """Convert the object to a native Python type.

        Args:
            obj: Object to convert
        """
        # If no custom converters are present, no need to do a conversion
        if not self._custom_converters:
            return obj

        # Look if object is present in the custom converters
        for custom_type in self._custom_converters:
            if isinstance(obj, custom_type):
                # First match will be used.
                # Keep in mind for inheritance you have think about child classes!
                # Make sure if you have parent and child classes registered separately, to first register the child classes!
                return self._custom_converters[custom_type](self, obj)

        # Lets convert
        match obj:
            # Convert the nested types
            case list():
                return [self(entry) for entry in obj]
            case set():
                return (self(entry) for entry in obj)
            case dict():
                return {k: self(v) for k, v in obj.items()}

            # Nothing to do here, since these are the accepted types
            case int() | float() | bool() | str():
                return obj

            # Type was not registered and is not one of the standards one
            case _:
                raise TypeError(
                    f"Object {obj} of type {type(obj)} can not be converted"
                )

    def __str__(self):
        """String representation of the Converter class."""
        string = "Converter with custom object (objects will be converted from top to bottom):"
        for k, v in self._custom_converters.items():
            string += f"\n\t{k}\t: {v}"

        return string
