from zocalo.mimas.classes import (
    MimasRecipeInvocation,
    MimasISPyBJobInvocation,
    MimasISPyBParameter,
    MimasISPyBSweep,
    MimasISPyBUnitCell,
    MimasISPyBSpaceGroup,
    zocalo_message,
)


def test_transformation_of_recipe_invocation():
    valid_invocation = MimasRecipeInvocation(dcid=1, recipe="string")
    zocdata = zocalo_message(valid_invocation)
    assert isinstance(zocdata, dict)


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
    zocdata = zocalo_message(valid_invocation)
    assert isinstance(zocdata, dict)


def test_validation_of_ispyb_parameters():
    valid = MimasISPyBParameter(key="key", value="value")
    zocdata = zocalo_message(valid)
    assert isinstance(zocdata, dict)

    zoclist = zocalo_message([valid, valid])
    assert isinstance(zoclist, list)
    assert len(zoclist) == 2
    assert zoclist[0] == zocdata
    assert zoclist[1] == zocdata


def test_validation_of_ispyb_sweeps():
    valid = MimasISPyBSweep(dcid=1, start=10, end=100)
    zocdata = zocalo_message(valid)
    assert isinstance(zocdata, dict)

    zoclist = zocalo_message((valid, valid))
    assert isinstance(zoclist, tuple)
    assert len(zoclist) == 2
    assert zoclist[0] == zocdata
    assert zoclist[1] == zocdata


def test_validation_of_ispyb_unit_cells():
    valid = MimasISPyBUnitCell(a=10, b=11, c=12, alpha=90, beta=91.0, gamma=92)
    zocdata = zocalo_message(valid)
    assert zocdata == (10, 11, 12, 90, 91.0, 92)


def test_validation_of_ispyb_space_groups():
    valid = MimasISPyBSpaceGroup(symbol="P 41 21 2")
    zocdata = zocalo_message(valid)
    assert zocdata == "P41212"
