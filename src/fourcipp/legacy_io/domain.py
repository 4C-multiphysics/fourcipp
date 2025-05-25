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
"""Domain io.

Once this section is implemented in 4C using InputSpec, this file can be
deleted.
"""

from functools import partial

from fourcipp.legacy_io.inline_dat import (
    _extract_all,
    _extract_enum,
    _extract_vector,
    inline_dat_read,
    to_dat_string,
)

DOMAIN_CASTING = {
    "LOWER_BOUND": partial(_extract_vector, entry_type=float, size=3),
    "UPPER_BOUND": partial(_extract_vector, entry_type=float, size=3),
    "INTERVALS": partial(_extract_vector, entry_type=int, size=3),
    "ROTATION": partial(_extract_vector, entry_type=float, size=3),
    "ELEMENTS": partial(_extract_all, entry_type=str),
    "PARTITION": partial(_extract_enum, choices=["auto", "structured"]),
}


def read_domain(lines: list[str]) -> dict:
    """Read domain section.

    Args:
        lines: List of lines.

    Returns:
        Domain section as dict
    """
    data = {}
    for line in lines:
        data.update(inline_dat_read(line.split(), DOMAIN_CASTING))
    return data


def write_domain(domain: dict) -> list[str]:
    """Write domain section.

    Args:
        domain: Domain section as dict

    Returns:
        Domain as list of lines
    """
    new_lines = []
    for k, v in domain.items():
        new_lines.append(f"{k} {to_dat_string(v)}")
    return new_lines
