import dataclasses
import itertools

import pytest

from zocalo.mimas.classes import (
    MimasScenario,
    MimasEvent,
    MimasExperimentType,
    MimasRunStatus,
    MimasDetectorClass,
    MimasISPyBUnitCell,
    MimasISPyBSpaceGroup,
    MimasISPyBSweep,
    MimasISPyBParameter,
    MimasRecipeInvocation,
    MimasISPyBJobInvocation,
    validate,
)


def test_validation_of_unknown_objects():
    for failing_object in (
        5,
        "string",
        b"bytestring",
        None,
        True,
        False,
        [],
        {},
        dict(),
    ):
        with pytest.raises(ValueError):
            validate(failing_object)


def test_validation_of_scenario():
    valid_scenario = MimasScenario(
        dcid=1,
        experimenttype=MimasExperimentType.OSC,
        event=MimasEvent.START,
        beamline="i03",
        unitcell=MimasISPyBUnitCell(a=10, b=10.0, c=10, alpha=90.0, beta=90, gamma=90),
        spacegroup=MimasISPyBSpaceGroup("P41212"),
        preferred_processing=None,
        runstatus=MimasRunStatus.SUCCESS,
        detectorclass=MimasDetectorClass.PILATUS,
    )
    validate(valid_scenario)

    # replacing individual values should fail validation
    for key, value in [
        ("dcid", "banana"),
        ("experimenttype", None),
        ("experimenttype", 1),
        ("event", MimasRecipeInvocation(dcid=1, recipe="invalid")),
        ("getsweepslistfromsamedcg", MimasRecipeInvocation(dcid=1, recipe="invalid"),),
        (
            "getsweepslistfromsamedcg",
            (MimasRecipeInvocation(dcid=1, recipe="invalid"),),
        ),
        ("getsweepslistfromsamedcg", MimasISPyBSweep(dcid=1, start=1, end=100),),
        ("getsweepslistfromsamedcg", ""),
        ("getsweepslistfromsamedcg", None),
        ("unitcell", False),
        ("unitcell", (10, 10, 10, 90, 90, 90)),
        ("unitcell", MimasRecipeInvocation(dcid=1, recipe="invalid"),),
        ("detectorclass", "ADSC"),
    ]:
        print(f"testing {key}: {value}")
        invalid_scenario = dataclasses.replace(valid_scenario, **{key: value})
        with pytest.raises(ValueError):
            validate(invalid_scenario)


def test_validation_of_recipe_invocation():
    valid_invocation = MimasRecipeInvocation(dcid=1, recipe="string")
    validate(valid_invocation)

    # replacing individual values should fail validation
    for key, value in [
        ("dcid", "banana"),
        ("recipe", MimasRecipeInvocation(dcid=1, recipe="invalid")),
        ("recipe", ""),
        ("recipe", None),
    ]:
        print(f"testing {key}: {value}")
        invalid_invocation = dataclasses.replace(valid_invocation, **{key: value})
        with pytest.raises(ValueError):
            validate(invalid_invocation)


def test_validation_of_ispyb_invocation():
    valid_invocation = MimasISPyBJobInvocation(
        dcid=1,
        autostart=True,
        comment="",
        displayname="",
        parameters=(MimasISPyBParameter(key="test", value="valid"),),
        recipe="string",
        source="automatic",
        sweeps=(MimasISPyBSweep(dcid=1, start=1, end=100),),
        triggervariables=(),
    )
    validate(valid_invocation)

    # replacing individual values should fail validation
    for key, value in [
        ("dcid", "banana"),
        ("autostart", "banana"),
        ("parameters", MimasRecipeInvocation(dcid=1, recipe="invalid")),
        ("parameters", (MimasRecipeInvocation(dcid=1, recipe="invalid"),)),
        ("parameters", MimasISPyBParameter(key="test", value="invalid")),
        ("parameters", ""),
        ("parameters", None),
        ("recipe", MimasRecipeInvocation(dcid=1, recipe="invalid")),
        ("recipe", ""),
        ("recipe", None),
        ("sweeps", MimasRecipeInvocation(dcid=1, recipe="invalid")),
        ("sweeps", (MimasRecipeInvocation(dcid=1, recipe="invalid"),)),
        ("sweeps", MimasISPyBSweep(dcid=1, start=1, end=100)),
        ("sweeps", ""),
        ("sweeps", None),
    ]:
        print(f"testing {key}: {value}")
        invalid_invocation = dataclasses.replace(valid_invocation, **{key: value})
        with pytest.raises(ValueError):
            validate(invalid_invocation)


def test_validation_of_ispyb_parameters():
    valid = MimasISPyBParameter(key="key", value="value")
    validate(valid)

    # replacing individual values should fail validation
    for key, value in [
        ("key", ""),
        ("key", 5),
        ("key", None),
        ("key", False),
        ("value", 5),
        ("value", None),
        ("value", False),
    ]:
        print(f"testing {key}: {value}")
        invalid = dataclasses.replace(valid, **{key: value})
        with pytest.raises(ValueError):
            validate(invalid)


def test_validation_of_ispyb_sweeps():
    valid = MimasISPyBSweep(dcid=1, start=10, end=100)
    validate(valid)

    # replacing individual values should fail validation
    for key, value in [
        ("dcid", ""),
        ("dcid", "1"),
        ("dcid", None),
        ("dcid", 0),
        ("start", ""),
        ("start", "5"),
        ("start", False),
        ("start", -3),
        ("end", ""),
        ("end", "5"),
        ("end", False),
        ("end", -3),
        ("end", 5),
    ]:
        print(f"testing {key}: {value}")
        invalid = dataclasses.replace(valid, **{key: value})
        with pytest.raises(ValueError):
            validate(invalid)


def test_validation_of_ispyb_unit_cells():
    valid = MimasISPyBUnitCell(a=10, b=11, c=12, alpha=90, beta=91.0, gamma=92)
    validate(valid)
    assert valid.string == "10,11,12,90,91.0,92"

    # replacing individual values should fail validation
    for key, value in itertools.chain(
        itertools.product(
            ("a", "b", "c", "alpha", "beta", "gamma"), (-10, 0, "", False)
        ),
        [("alpha", 180), ("beta", 180), ("gamma", 180)],
    ):
        print(f"testing {key}: {value}")
        invalid = dataclasses.replace(valid, **{key: value})
        with pytest.raises(ValueError):
            validate(invalid)


def test_validataion_of_ispyb_space_groups():
    valid = MimasISPyBSpaceGroup(symbol="P 41 21 2")
    validate(valid)
    assert valid.string == "P41212"

    invalid = MimasISPyBSpaceGroup(symbol="P 5")
    with pytest.raises(ValueError):
        validate(invalid)
