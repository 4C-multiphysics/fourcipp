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
"""Test knotvectors io."""

import pytest

from fourcipp.legacy_io.knotvectors import read_knotvectors, write_knotvectors


@pytest.fixture(name="reference_knotvector_lines")
def fixture_reference_knotvector_lines():
    """Reference lines."""
    return [
        "NURBS_DIMENSION                       2",
        "BEGIN                                 NURBSPATCH",
        "ID                                    1",
        "NUMKNOTS                              7",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "0.0",
        "0.0",
        "0.5",
        "1.0",
        "1.0",
        "1.0",
        "",
        "NUMKNOTS                              8",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "0.0",
        "0.0",
        "0.3333333333333333",
        "0.6666666666666666",
        "1.0",
        "1.0",
        "1.0",
        "END                                   NURBSPATCH",
        "NURBS_DIMENSION                       2",
        "BEGIN                                 NURBSPATCH",
        "ID                                    2",
        "NUMKNOTS                              7",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "0.0",
        "0.0",
        "0.5",
        "1.0",
        "1.0",
        "1.0",
        "NUMKNOTS                              8",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "0.0",
        "0.0",
        "0.3333333333333333",
        "0.6666666666666666",
        "1.0",
        "1.0",
        "1.0",
        "END                                   NURBSPATCH",
    ]


def test_knotvectors_read_and_write(reference_knotvector_lines):
    """Test read and write knotvectors."""
    lines = write_knotvectors(read_knotvectors(reference_knotvector_lines))
    for k in range(len(reference_knotvector_lines)):
        assert reference_knotvector_lines[k].split() == lines[k].split()


@pytest.fixture(name="reference_knotvector_lines_single_dimension")
def fixture_reference_knotvector_lines_single_dimension():
    """Reference lines."""
    return [
        "NURBS_DIMENSION                       2",
        "BEGIN                                 NURBSPATCH",
        "ID                                    1",
        "NUMKNOTS                              7",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "0.0",
        "0.0",
        "0.5",
        "1.0",
        "1.0",
        "1.0",
        "",
        "NUMKNOTS                              8",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "0.0",
        "0.0",
        "0.3333333333333333",
        "0.6666666666666666",
        "1.0",
        "1.0",
        "1.0",
        "END                                   NURBSPATCH",
        "BEGIN                                 NURBSPATCH",
        "ID                                    2",
        "NUMKNOTS                              7",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "0.0",
        "0.0",
        "0.5",
        "1.0",
        "1.0",
        "1.0",
        "NUMKNOTS                              8",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "0.0",
        "0.0",
        "0.3333333333333333",
        "0.6666666666666666",
        "1.0",
        "1.0",
        "1.0",
        "END                                   NURBSPATCH",
    ]


def test_knotvectors_single_dimension_read_and_write(
    fixture_reference_knotvector_lines_single_dimension, reference_knotvector_lines
):
    """Test read and write knotvectors."""
    lines = write_knotvectors(
        read_knotvectors(fixture_reference_knotvector_lines_single_dimension)
    )
    for k in range(len(reference_knotvector_lines)):
        assert reference_knotvector_lines[k].split() == lines[k].split()


def test_wrong_knotvectors_dimension_mismatch():
    """Test knotvectors with mismatching dimension."""
    invalid_knotvectors = [
        "NURBS_DIMENSION                       2",
        "BEGIN                                 NURBSPATCH",
        "ID                                    1",
        "NUMKNOTS                              7",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "0.0",
        "0.0",
        "0.5",
        "1.0",
        "1.0",
        "1.0",
        "END                                NURBSPATCH",
    ]

    with pytest.raises(ValueError, match="Expected 2 knot vectors, got 1"):
        read_knotvectors(invalid_knotvectors)


def test_unknown_keyword():
    """Test unknown keyword."""
    invalid_knotvectors = [
        "NURBS_DIMENSION                       2",
        "BEGIN                                 NURBSPATCH",
        "ID                                    1",
        "unknown_keyword 1",
        "NUMKNOTS                              1",
        "DEGREE                                2",
        "TYPE                                  Interpolated",
        "0.0",
        "END                                NURBSPATCH",
    ]
    with pytest.raises(ValueError, match="Could not read line"):
        read_knotvectors(invalid_knotvectors)


def test_invalid_line_list_length():
    """Test invalid line_list length."""
    invalid_knotvectors = [
        "NURBS_DIMENSION                       2",
        "too many entries",
    ]
    with pytest.raises(ValueError, match="Could not read line"):
        read_knotvectors(invalid_knotvectors)
