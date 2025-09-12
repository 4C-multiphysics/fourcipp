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
"""Not set utils."""


class NotSet:
    """Not set object."""

    def __init__(self, expected: object = object) -> None:
        """Not set object.

        Args:
            expected: Expected object to to display
        """
        self.expected = expected

    def __str__(self) -> str:  # pragma: no cover
        """String method."""
        return f"NotSet({self.expected})"

    def __repr__(self) -> str:  # pragma: no cover
        """Representation method."""
        return f"NotSet({self.expected})"


NOT_SET = NotSet()


def check_if_set(obj: object) -> bool:
    """Check if object or is NotSet.

    Args:
        obj: Object to check

    Returns:
        True if object is set
    """
    # Check if object is not of type _NotSet, i.e. it has a value
    return not isinstance(obj, NotSet)


def pop_arguments(key: str, default: object = NOT_SET) -> tuple:
    """Create arguments for the pop method.

    We need this utility since pop is not implemented using kwargs, instead the default is checked
     via the number of arguments.

    Args:
        key: Key to pop the value for
        default: Default value to return in case of the pop value.

    Returns:
        Arguments for pop
    """
    if check_if_set(default):
        return (key, default)
    else:
        return (key,)
