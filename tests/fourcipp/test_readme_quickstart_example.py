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
"""Test read me example."""

import pathlib
import subprocess

import pytest

from fourcipp.fourc_input import FourCInput


@pytest.fixture(name="readme_example")
def fixture_readme_example(tmp_path):
    """Extract readme example and create file."""

    input_file_path = tmp_path / "other_input.4C.yaml"
    fourc_input = FourCInput()
    fourc_input["TITLE"] = {"some": "thing"}
    fourc_input.dump(input_file_path)

    readme = pathlib.Path(__file__).parents[2] / "README.md"
    example = readme.read_text(encoding="utf-8")
    example_marker = "<!--example, do not remove this comment-->"
    example = example.split(example_marker)[1]

    # Add missing path
    escaped_path = repr(str(input_file_path))  # For windows compatibility
    example = [f"input_file_path = {escaped_path}"] + [
        line for line in example.split("\n") if not "```" in line
    ]
    example = "\n".join(example)
    example_path = tmp_path / "example.py"

    # Create file
    example_path.write_text(example)

    return example_path


def test_readme_example(readme_example, tmp_path):
    """Test if the example runs."""
    command = f"python {readme_example} > {tmp_path / 'output.log'} 2>&1"
    return_code = subprocess.call(command, shell=True)  # nosec

    # Exit code -> script failed
    if return_code:
        raise Exception(
            f"Example run failed: {command}\n\nOutput: {(tmp_path / 'output.log').read_text(encoding='utf-8')}"
        )
