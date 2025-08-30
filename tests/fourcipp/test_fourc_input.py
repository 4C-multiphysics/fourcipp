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

import contextlib
import pathlib
import subprocess
import time
from collections.abc import Callable

import pytest

from fourcipp import CONFIG
from fourcipp.fourc_input import (
    FourCInput,
    UnknownSectionException,
)
from fourcipp.utils.cli import modify_input_with_defaults
from fourcipp.utils.validation import ValidationError

from ..fourcipp.legacy_io.test_element import (  # noqa: TID252
    generate_elements_from_metadatafile,
)


@pytest.fixture(name="section_names")
def fixture_section_names():
    """Section names."""
    section_name_1 = CONFIG.fourc_metadata["sections"]["specs"][0]["name"]
    section_name_2 = CONFIG.fourc_metadata["sections"]["specs"][1]["name"]
    return section_name_1, section_name_2


@pytest.fixture(name="section_names_2")
def fixture_section_names_2():
    """More section names."""
    section_name_3 = CONFIG.fourc_metadata["sections"]["specs"][2]["name"]
    section_name_4 = CONFIG.fourc_metadata["sections"]["specs"][3]["name"]
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


@pytest.mark.parametrize("method", ("combine_sections", "overwrite_sections"))
def test_combine_sections_inputs(
    fourc_input, fourc_input_2, section_names, section_names_2, method
):
    """Test combine sections inputs."""
    combined_section_names = list(section_names) + list(section_names_2)

    getattr(fourc_input, method)(fourc_input_2)

    assert fourc_input.get_section_names() == combined_section_names


@pytest.mark.parametrize("method", ("combine_sections", "overwrite_sections"))
def test_combine_sections_dicts(
    fourc_input, fourc_input_2, section_names, section_names_2, method
):
    """Test combine sections from dict."""
    combined_section_names = list(section_names) + list(section_names_2)

    getattr(fourc_input, method)(fourc_input_2.sections)

    assert fourc_input.get_section_names() == combined_section_names


def test_combine_sections_failure_type(fourc_input):
    """Test combine sections inputs failure due to wrong type."""
    with pytest.raises(TypeError, match="Cannot combine sections between"):
        fourc_input.combine_sections("ups not a input object :/")


def test_combine_sections_failure_doubled_data(fourc_input):
    """Test combine sections failure due to doubled section."""
    with pytest.raises(ValueError, match="Section"):
        fourc_input.combine_sections(fourc_input.copy())


def test_combine_sections_failure_doubled_data_dict(fourc_input):
    """Test combine sections failure due to doubled section."""
    with pytest.raises(ValueError, match="Section"):
        fourc_input.combine_sections(fourc_input.copy().sections)


def test_overwrite_sections_new_section_dict(fourc_input):
    """Test overwriting sections that does not exist."""
    fourc_input.overwrite_sections({"TITLE": "new title"})
    assert fourc_input["TITLE"] == "new title"


def test_overwrite_sections_existing_section_dict(fourc_input):
    """Test overwriting sections that already exist."""
    fourc_input["TITLE"] = "new title"
    fourc_input.overwrite_sections({"TITLE": "super new title"})
    assert fourc_input["TITLE"] == "super new title"


def test_overwrite_sections_new_section_input(fourc_input):
    """Test overwriting sections that does not exist."""
    fourc_input.overwrite_sections(FourCInput({"TITLE": "new title"}))
    assert fourc_input["TITLE"] == "new title"


def test_overwrite_sections_existing_section_input(fourc_input):
    """Test overwriting sections that already exist."""
    fourc_input["TITLE"] = "new title"
    fourc_input.overwrite_sections(FourCInput({"TITLE": "super new title"}))
    assert fourc_input["TITLE"] == "super new title"


def test_apply_default(tmp_path):
    """Test using a default file.

    4C default file with a section that is not in the input file and one
    that is. A section containing a list should not be added.
    """

    # Creating the default file
    path_to_default = tmp_path / "default.4C.yaml"
    default_input = FourCInput({"PROBLEM TYPE": {"PROBLEMTYPE": "default problemtype"}})
    default_input["PROBLEM SIZE"] = {"DIM": 3}
    default_input.dump(path_to_default)

    # writing some entries to the current fourc_input
    fourc_input = FourCInput({"SOLVER 1": {"NAME": "current title"}})
    fourc_input["PROBLEM TYPE"] = {"PROBLEMTYPE": "current problemtype"}

    # Applying the defaults
    fourc_input.apply_user_defaults(path_to_default)

    # Only in current input
    assert fourc_input["SOLVER 1"] == {"NAME": "current title"}
    # Defined in both default and current input -> do not overwrite with the default
    assert fourc_input["PROBLEM TYPE"] == {"PROBLEMTYPE": "current problemtype"}
    # Defined in default, not in current input -> should be taken
    assert fourc_input["PROBLEM SIZE"] == {"DIM": 3}
    # should not be taken even though it is in the default file, because it is a list
    assert not "MATERIALS" in fourc_input


def test_apply_user_defaults(
    fourc_input, fourc_input_2, fourc_input_combined, tmp_path
):
    """Test for applying user defaults from the file assigned in the config."""

    # change user_default_path to tmp_path/user_defaults.4C.yaml
    # This cannot be done using the cli function change_user_defaults_path
    CONFIG.user_defaults_path = tmp_path / "user_defaults.4C.yaml"
    # dump fourc_input to tmp_path/current_input.4C.yaml
    fourc_input.dump(tmp_path / "current_input.4C.yaml")
    # dump fourc_input_2 to user_default_path
    fourc_input_2.dump(tmp_path / "user_defaults.4C.yaml")
    # Now comes the function to be tested:
    # apply_user_defaults to fourc_input
    modify_input_with_defaults(tmp_path / "current_input.4C.yaml", True)
    # should result in fourc_input_combined
    defaulted_input = FourCInput.from_4C_yaml(tmp_path / "current_input.4C.yaml")
    assert defaulted_input == fourc_input_combined


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
    fourc_input_combined, tmp_path, section_names
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

    files = [
        "ale2d_solid_lin.4C.yaml",
        "beam3eb_genalpha_lineload_dynamic.4C.yaml",
        "beam3r_herm2line3_static_beam_to_solid_volume_meshtying_2d-3d.4C.yaml",
        "contact3D_quad_tet10.4C.yaml",
        "elch_2D_porousMediumHomo_SSPP.4C.yaml",
        "f2_nurbs9_dc_drt.4C.yaml",
        "fsi_dc_mono_slss_msht.4C.yaml",
        "particle_dem_1d_adhesion_RegDMT.4C.yaml",
        "poro_3D_tet4.4C.yaml",
        "reduced_lung_3_aw_2_tu.4C.yaml",
        "scatra_chemo_h27.4C.yaml",
        "solid_ele_tet4_Standard_linear.4C.yaml",
        "tsi_meshtying_nurbs.4C.yaml",
        "xfsi_comp_struct_fsi_2D_mono_slip.4C.yaml",
        "xfsi_3D_boxes.4C.yaml",  # test domain
    ]

    return [str(test_files_directory / file) for file in files]


FOURC_TEST_INPUT_FILES = get_4C_test_input_files()


class SubprocessError(Exception):
    """Subprocess failure."""


@pytest.mark.skipif(CONFIG.name != "4C_docker_main", reason="Not using docker config.")
@pytest.mark.parametrize("fourc_file", FOURC_TEST_INPUT_FILES)
def test_roundtrip_test(fourc_file, tmp_path):
    """Roundtrip test."""
    fourc_file = pathlib.Path(fourc_file)

    # Load 4C input test file
    fourc_input = FourCInput.from_4C_yaml(fourc_file)

    # Delete the original file (we need to dump the file in the original location to ensure that associated files, i.e., xml solver files, are still present)
    fourc_file.unlink()

    # Dump out again
    fourc_input.dump(fourc_file, validate=True)

    # Command
    command = (
        f"/home/user/4C/build/4C {fourc_file} xxx > {tmp_path / 'output.log'} 2>&1"
    )

    # Run 4C with the dumped input
    return_code = subprocess.call(command, shell=True)  # nosec

    # Exit code -> 4C failed
    if return_code:
        raise SubprocessError(
            f"Input file failed for {fourc_file}.\n\n4C command: {command}\n\nOutput: {(tmp_path / 'output.log').read_text()}"
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


@pytest.mark.parametrize(
    "fourc_input,error_context, sections_only",
    [
        (
            FourCInput(sections={"TITLE": "some title"}),
            pytest.raises(ValidationError),
            False,
        ),
        (
            FourCInput(
                sections={
                    "TITLE": "some title",
                    "PROBLEM TYPE": {"PROBLEMTYPE": "Fluid"},
                }
            ),
            contextlib.nullcontext(),  # No error
            False,
        ),
        (
            FourCInput(sections={"TITLE": "some title"}),
            contextlib.nullcontext(),
            True,
        ),
        (
            FourCInput(
                sections={
                    "TITLE": "some title",
                    "PROBLEM TYPE": {"PROBLEMTYPE": "Fluid"},
                }
            ),
            contextlib.nullcontext(),  # No error
            True,
        ),
    ],
)
def test_validation(fourc_input, error_context, sections_only):
    """Test the validation."""
    with error_context:
        fourc_input.validate(sections_only=sections_only)


def create_dummy_elements() -> dict:
    """Create dummy elements for the performance test.

    Loops over all elements from the metadata file and creates
    3000 dummy elements for each element type.

    Returns:
        dict: Dictionary with dummy elements.
    """

    reference_elements = generate_elements_from_metadatafile()

    dummy_elements: dict[str, list[str]] = {"STRUCTURE ELEMENTS": []}

    for element in reference_elements:
        for i in range(1, 3000):
            dummy_elements["STRUCTURE ELEMENTS"].append(
                f"{i} {' '.join(element.split()[1:])}"
            )

    return dummy_elements


def evaluate_execution_time(fct: Callable, args: dict) -> float:
    """Evaluate execution time of a function.

    Args:
        fct: Function to test.
        args: Arguments to pass to the function.

    Returns:
        float: Execution time in seconds.
    """

    start_time = time.time()
    fct(**args)
    end_time = time.time()

    return end_time - start_time


def save_timings(timings: dict, file: str) -> None:
    """Save timings to a file.

    Args:
        timings: Dictionary with timings.
        file: Name of the markdown file to save the timings.
    """

    if not file.endswith(".md"):
        raise ValueError("File must be a markdown file ending with .md!")

    with open(file, "w", encoding="utf-8") as f:
        f.write("# Performance Timings :rocket:\n\n")
        f.write("| Operation         | Time (seconds)  |\n")
        f.write("|-------------------|-----------------|\n")
        for operation, time_taken in timings.items():
            f.write(f"| {operation:<17} | {time_taken:10.6f}      |\n")


@pytest.mark.performance
def test_performance(tmp_path) -> None:
    """Test performance of core functions of FourCInput."""

    dummy_elements = create_dummy_elements()

    fourc_input = FourCInput()

    timings = {}

    # Evaluate execution time of adding elements to input file
    timings["add_elements"] = evaluate_execution_time(
        fourc_input.combine_sections, args={"other": dummy_elements}
    )

    # Evaluate execution time of validating the input file
    timings["validate"] = evaluate_execution_time(
        fourc_input.validate, args={"sections_only": True}
    )

    # Evaluate performance of dumping the input file
    timings["dump"] = evaluate_execution_time(
        fourc_input.dump,
        args={"input_file_path": tmp_path / "performance_test.4C.yaml"},
    )

    # Evaluate performance of loading the input file
    timings["load_from_file"] = evaluate_execution_time(
        FourCInput.from_4C_yaml,
        args={"input_file_path": tmp_path / "performance_test.4C.yaml"},
    )

    save_timings(timings, "timings.md")
