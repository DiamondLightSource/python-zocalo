import functools

from zocalo.mimas.core import run
from zocalo.mimas.classes import (
    MimasScenario,
    MimasExperimentType,
    MimasRunStatus,
    MimasEvent,
    zocalo_command_line,
    validate,
)


def get_zocalo_commands(scenario):
    commands = set()
    actions = run(scenario)
    for a in actions:
        validate(a)
        commands.add(zocalo_command_line(a).strip())
    return commands


def test_bl_start():
    dcid = 5918093
    scenario = functools.partial(
        MimasScenario,
        dcid=dcid,
        experimenttype=MimasExperimentType.ENERGY_SCAN,
        beamline="bl",
        proposalcode="ev",
        runstatus=MimasRunStatus.SUCCESS,
    )
    assert get_zocalo_commands(scenario(event=MimasEvent.START)) == {
        f"zocalo.go -r exafs-qa {dcid}",
    }


def test_bl_end():
    dcid = 5918093
    scenario = functools.partial(
        MimasScenario,
        dcid=dcid,
        experimenttype=MimasExperimentType.XRF_MAP,
        beamline="bl",
        runstatus=MimasRunStatus.SUCCESS,
    )
    assert get_zocalo_commands(scenario(event=MimasEvent.END)) == {
        f"ispyb.job --new --dcid={dcid} --source=automatic --recipe=pymca   --display='PyMCA Fitter' --trigger",
    }
