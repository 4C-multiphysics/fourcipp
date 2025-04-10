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
"""Test fourc input."""

import pathlib
import subprocess

import pytest

from fourcipp import CONFIG
from fourcipp.fourc_input import FourCInput, UnknownSectionException


@pytest.fixture(name="section_names")
def fixture_section_names():
    """Section names."""
    section_name_1 = CONFIG["4C_metadata"]["sections"][0]["name"]
    section_name_2 = CONFIG["4C_metadata"]["sections"][1]["name"]
    return section_name_1, section_name_2


@pytest.fixture(name="section_names_2")
def fixture_section_names_2():
    """More section names."""
    section_name_3 = CONFIG["4C_metadata"]["sections"][2]["name"]
    section_name_4 = CONFIG["4C_metadata"]["sections"][3]["name"]
    return section_name_3, section_name_4


@pytest.fixture(name="dummy_data")
def fixture_dummy_data():
    """Dummy data for the section."""
    return {"some": "data"}


@pytest.fixture(name="fourc_input")
def fixture_fourc_input(section_names, dummy_data):
    """First input object."""
    section_name_1, section_name_2 = section_names
    fourc_input = FourCInput(
        sections={
            section_name_1: dummy_data,
            section_name_2: dummy_data,
        }
    )
    return fourc_input


@pytest.fixture(name="fourc_input_with_legacy_section")
def fixture_fourc_input_with_legacy_section(fourc_input):
    """Input object with a legacy section."""
    # Copy the input
    new_input = fourc_input.copy()

    # Add a legacy section
    new_input["DNODE-NODE TOPOLOGY"] = ["NODE 1 DNODE 1"]

    return new_input


@pytest.fixture(name="fourc_input_2")
def fixture_fourc_input_2(section_names_2, dummy_data):
    """Second input object."""
    section_name_1, section_name_2 = section_names_2
    fourc_input = FourCInput(
        sections={
            section_name_1: dummy_data,
            section_name_2: dummy_data,
        }
    )
    return fourc_input


@pytest.fixture(name="fourc_input_combined")
def fixture_joined(section_names, section_names_2, dummy_data):
    """Joined input object."""
    section_name_1, section_name_2 = section_names
    section_name_3, section_name_4 = section_names_2
    fourc_input = FourCInput(
        sections={
            section_name_1: dummy_data,
            section_name_2: dummy_data,
            section_name_3: dummy_data,
            section_name_4: dummy_data,
        }
    )
    return fourc_input


def test_str(fourc_input):
    """Assert if the string representations return a string."""
    assert isinstance(fourc_input.__str__(), str)


def test_rpr(fourc_input):
    """Assert if the string representations return a string."""
    assert isinstance(fourc_input.__repr__(), str)


def test_set_section(fourc_input, section_names, section_names_2, dummy_data):
    """Test setting section."""
    fourc_input[section_names_2[0]] = dummy_data
    fourc_input[section_names_2[1]] = dummy_data

    combined_section_names = list(section_names) + list(section_names_2)
    assert fourc_input.get_section_names() == combined_section_names


def test_set_section_failure(fourc_input, dummy_data):
    """Test setting section failure."""
    with pytest.raises(UnknownSectionException, match="Unknown section"):
        fourc_input["not existing section"] = dummy_data


def test_get_section_failure(fourc_input):
    """Test getting section failure."""
    with pytest.raises(UnknownSectionException, match="Section"):
        fourc_input["not existing section"]


def test_set_legacy_section_wrong_type(fourc_input):
    """Test setting section."""
    with pytest.raises(TypeError, match="Section"):
        fourc_input["DNODE-NODE TOPOLOGY"] = "ups not a list or dict"


@pytest.mark.parametrize("data", [{"a": "dict"}, [{"b": "also dict"}]])
def test_set_legacy_section_from_dict(fourc_input, data):
    """Test setting section from dict or list of dicts."""
    fourc_input["DNODE-NODE TOPOLOGY"] = data
    assert fourc_input["DNODE-NODE TOPOLOGY"] == data


def test_pop(fourc_input, section_names, dummy_data):
    """Test pop."""
    data = fourc_input.pop(section_names[0])
    assert data == dummy_data
    assert section_names[0] not in fourc_input


def test_pop_with_default(fourc_input, section_names_2):
    """Test pop with default."""
    data = fourc_input.pop(section_names_2[0], "default value")
    assert data == "default value"


def test_pop_but_no_default(fourc_input, section_names_2):
    """Test pop with no default."""
    with pytest.raises(UnknownSectionException, match="Section"):
        fourc_input.pop(section_names_2[0])


def test_pop_with_default_but_set(fourc_input, section_names, dummy_data):
    """Test pop with default."""
    data = fourc_input.pop(section_names[0], "default value")
    assert data == dummy_data


def test_pop_failure_unknown_section(fourc_input):
    """Test pop failure due to unknown section."""

    with pytest.raises(UnknownSectionException, match="Unknown section"):
        fourc_input.pop("invalid section", "default value")


def test_items(fourc_input, section_names, dummy_data):
    """Test itemize."""
    for k, v in fourc_input.items():
        assert k in section_names
        assert v == dummy_data


def test_contains(fourc_input):
    """Test if section is contained."""
    assert fourc_input.get_section_names()[0] in fourc_input


def test_not_contains(fourc_input):
    """Test if section is not contained."""
    assert not "some section" in fourc_input


def test_join_inputs(fourc_input, fourc_input_2, section_names, section_names_2):
    """Join inputs."""
    combined_section_names = list(section_names) + list(section_names_2)
    fourc_input.join(fourc_input_2)

    assert fourc_input.get_section_names() == combined_section_names


def test_join_inputs_failure(fourc_input):
    """Join inputs failure due to wrong type."""
    with pytest.raises(TypeError, match="Can not join"):
        fourc_input.join("ups not a input object :/")


def test_join_inputs_failure_doubled_data(fourc_input):
    """Join inputs failure due to doubled data."""
    with pytest.raises(ValueError, match="Section"):
        fourc_input.join(fourc_input)


def test_add(fourc_input, fourc_input_2, fourc_input_combined):
    """Test adding inputs."""
    added_input = fourc_input + fourc_input_2

    assert added_input == fourc_input_combined
    assert added_input != fourc_input
    assert added_input != fourc_input_2


def test_equal(fourc_input):
    """Test for equal inputs."""
    assert fourc_input.sections == fourc_input.copy().sections


def test_equal_failure(fourc_input):
    """Test for equal failure."""
    with pytest.raises(TypeError, match="Can not compare types"):
        assert fourc_input == "wrong type"


def test_not_equal(fourc_input, fourc_input_2):
    """Test for non-equal inputs."""
    assert not fourc_input == fourc_input_2


def test_load_includes(fourc_input, fourc_input_2, fourc_input_combined, tmp_path):
    """Test loading includes."""
    path_to_other_sections = tmp_path / "split_data.4C.yaml"
    fourc_input_2.dump(path_to_other_sections)

    fourc_input["INCLUDES"] = [str(path_to_other_sections)]

    fourc_input.load_includes()

    assert fourc_input == fourc_input_combined


def test_split(fourc_input, fourc_input_2, fourc_input_combined, section_names_2):
    """Test split."""
    first, second = fourc_input_combined.split(section_names_2)

    assert first == fourc_input
    assert second == fourc_input_2


def test_dump_with_includes(
    fourc_input_combined, tmp_path, section_names, section_names_2
):
    """Test dump with includes."""
    path_1 = tmp_path / "path_1.4C.yaml"
    path_2 = tmp_path / "path_2.4C.yaml"

    fourc_input_combined.dump_with_includes(section_names, path_1, path_2)

    reloaded = FourCInput.from_4C_yaml(path_1)
    assert reloaded.get_section_names() == list(section_names_2) + ["INCLUDES"]


def test_dump_with_includes_invert_sections(
    fourc_input_combined, tmp_path, section_names, section_names_2
):
    """Test dump with includes with invert sections."""
    path_1 = tmp_path / "path_1.4C.yaml"
    path_2 = tmp_path / "path_2.4C.yaml"

    fourc_input_combined.dump_with_includes(
        section_names, path_1, path_2, invert_sections=True
    )

    reloaded = FourCInput.from_4C_yaml(path_1)
    assert reloaded.get_section_names() == list(section_names) + ["INCLUDES"]


def get_4C_test_input_files():
    """Get all input test files in 4C docker image."""
    test_files_directory = pathlib.Path("/home/user/4C/tests/input_files")

    if not test_files_directory.exists():
        return []

    return [
        str(file_path) for file_path in sorted(test_files_directory.glob("*.4C.yaml"))
    ]


FOURC_TEST_INPUT_FILES = get_4C_test_input_files()


@pytest.mark.skipif(not FOURC_TEST_INPUT_FILES, reason="4C input files not found.")
@pytest.mark.parametrize("fourc_file", FOURC_TEST_INPUT_FILES)
def test_roundtrip_test(fourc_file, tmp_path):
    """Roundtrip test."""
    fourc_file = pathlib.Path(fourc_file)

    # Load 4C input test file
    fourc_input = FourCInput.from_4C_yaml(fourc_file)

    # Dump out again
    roundtrip_file_path = tmp_path / fourc_file.name
    fourc_input.dump(roundtrip_file_path, validate=True)

    # Command
    command = f"/home/user/4C/build/4C {roundtrip_file_path} xxx > {tmp_path / 'output.log'} 2>&1"

    # Run 4C with the dumped input
    return_code = subprocess.call(command, shell=True)  # nosec

    # Exit code -> 4C failed
    if return_code:
        raise Exception(
            f"Input file failed for {fourc_file}.\n\n4C command: {command}\n\nOutput: {tmp_path / 'output.log'}"
        )


def test_extract_header_sections(fourc_input, fourc_input_with_legacy_section):
    """Test the header extraction."""

    # Extract the header
    header = fourc_input_with_legacy_section.extract_header()

    assert header == fourc_input


def test_load_from_yaml(fourc_input_with_legacy_section, tmp_path):
    """Test load from yaml file."""
    path_to_yaml = tmp_path / "fourc_input.4C.yaml"
    fourc_input_with_legacy_section.dump(path_to_yaml)

    assert fourc_input_with_legacy_section == FourCInput.from_4C_yaml(path_to_yaml)


def test_load_from_yaml_header_only(
    fourc_input, fourc_input_with_legacy_section, tmp_path
):
    """Test load from yaml file using header only."""
    path_to_yaml = tmp_path / "fourc_input.4C.yaml"
    fourc_input_with_legacy_section.dump(path_to_yaml)

    assert fourc_input == FourCInput.from_4C_yaml(path_to_yaml, header_only=True)


def test_compare(fourc_input):
    """Test compare function."""
    copy_input = fourc_input.copy()
    assert fourc_input.compare(copy_input)


def test_compare_failure(fourc_input, fourc_input_2):
    """Test compare function failure."""
    assert not fourc_input.compare(fourc_input_2)


def test_compare_failure_with_exception(fourc_input, fourc_input_2):
    """Test compare function failure."""
    with pytest.raises(AssertionError):
        fourc_input.compare(fourc_input_2, raise_exception=True)
