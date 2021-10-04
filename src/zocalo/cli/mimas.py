""" Interrogates Mimas. Shows what would happen for a given datacollection ID"""
import os
import argparse
import errno
import logging

import workflows.recipe
import zocalo.configuration

try:
    from zocalo.ispyb.filter import ispyb_filter, ispybtbx
except ImportError:
    print("Error: zocalo.mimas requires ispyb to be installed")
    exit(1)

from zocalo.mimas.core import run as mimas_run
from zocalo.mimas.classes import (
    MimasEvent,
    MimasScenario,
    MimasExperimentType,
    MimasRunStatus,
    MimasDCClass,
    MimasISPyBSweep,
    MimasISPyBUnitCell,
    MimasISPyBSpaceGroup,
    MimasDetectorClass,
    MimasRecipeInvocation,
    MimasISPyBJobInvocation,
    validate,
    zocalo_command_line,
)

logging.basicConfig(level=logging.WARNING)


_readable = {
    MimasEvent.START: "start of data collection",
    MimasEvent.END: "end of data collection",
}


def get_recipe_triggers(recipe_path, recipefile):
    try:
        with open(os.path.join(recipe_path, recipefile + ".json"), "r") as rcp:
            named_recipe = workflows.recipe.Recipe(recipe=rcp.read())
    except ValueError as e:
        raise ValueError("Error reading recipe '%s': %s", recipefile, str(e))
    except IOError as e:
        if e.errno == errno.ENOENT:
            raise ValueError(
                f"Message references non-existing recipe {recipefile}. Recipe path is {recipe_path}",
            )
        raise

    triggers = []
    for step_id, step in named_recipe.recipe.items():
        if isinstance(step, dict):
            if step["queue"] == "trigger":
                triggers.append(
                    {
                        "target": step["parameters"]["target"],
                        "comment": step["parameters"]["comment"],
                        "automatic": step["parameters"]["automatic"],
                    }
                )

    return triggers


def get_scenarios(dcid):
    _, ispyb_info = ispyb_filter({}, {"ispyb_dcid": dcid})

    if len(ispyb_info.keys()) == 1:
        exit()

    cell = ispyb_info.get("ispyb_unit_cell")
    if cell:
        cell = MimasISPyBUnitCell(*cell)
    else:
        cell = None

    spacegroup = ispyb_info.get("ispyb_space_group")
    if spacegroup:
        spacegroup = MimasISPyBSpaceGroup(spacegroup)
    else:
        spacegroup = None

    experimenttype = ispyb_info["ispyb_experimenttype"]
    if not experimenttype or not isinstance(experimenttype, str):
        print(f"Invalid Mimas request rejected (experimenttype = {experimenttype!r})")
        exit()

    try:
        experimenttype_safe = experimenttype.replace(" ", "_")
        experimenttype_mimas = MimasExperimentType[experimenttype_safe.upper()]
    except KeyError:
        print(f"Invalid Mimas request (Experiment type = {experimenttype!r})")
        experimenttype_mimas = MimasExperimentType.UNDEFINED

    dc_class = ispyb_info.get("ispyb_dc_class")
    if dc_class and dc_class["grid"]:
        dc_class_mimas = MimasDCClass.GRIDSCAN
    elif dc_class and dc_class["screen"]:
        dc_class_mimas = MimasDCClass.SCREENING
    elif dc_class and dc_class["rotation"]:
        dc_class_mimas = MimasDCClass.ROTATION
    else:
        dc_class_mimas = MimasDCClass.UNDEFINED

    run_status = ispyb_info["ispyb_dc_info"]["runStatus"].lower()
    if "success" in run_status:
        run_status_mimas = MimasRunStatus.SUCCESS
    elif "fail" in run_status:
        run_status_mimas = MimasRunStatus.FAILURE
    else:
        run_status_mimas = MimasRunStatus.UNKNOWN

    detectorclass = (
        MimasDetectorClass.EIGER
        if ispyb_info["ispyb_detectorclass"] == "eiger"
        else MimasDetectorClass.PILATUS
    )
    scenarios = []
    for event in (MimasEvent.START, MimasEvent.END):
        scenario = MimasScenario(
            dcid=dcid,
            dcclass=dc_class_mimas,
            experimenttype=experimenttype_mimas,
            event=event,
            beamline=ispyb_info["ispyb_beamline"],
            proposalcode=ispyb_info["ispyb_dc_info"].get("proposalCode"),
            runstatus=run_status_mimas,
            spacegroup=spacegroup,
            unitcell=cell,
            getsweepslistfromsamedcg=tuple(
                MimasISPyBSweep(*sweep)
                for sweep in ispyb_info.get("ispyb_related_sweeps", [])
            ),
            preferred_processing=ispyb_info.get("ispyb_preferred_processing"),
            detectorclass=detectorclass,
        )
        try:
            validate(scenario)
        except ValueError:
            print(
                f"Can not generate a valid Mimas scenario for {_readable.get(scenario.event)} {dcid}"
            )
            raise
        scenarios.append(scenario)
    return scenarios


def run(args=None):
    zc = zocalo.configuration.from_file()
    zc.activate()

    parser = argparse.ArgumentParser(usage="zocalo.mimas [options] dcid")
    parser.add_argument("dcids", type=int, nargs="+", help="Data collection ids")
    parser.add_argument("-?", action="help", help=argparse.SUPPRESS)
    parser.add_argument(
        "--commands",
        "-c",
        action="store_true",
        dest="show_commands",
        default=False,
        help="Show commands that would trigger the individual processing steps",
    )
    zc.add_command_line_options(parser)

    args = parser.parse_args(args)

    i = ispybtbx()

    for dcid in args.dcids:
        dc_info = i.get_dc_info(dcid)

        for scenario in get_scenarios(dcid):
            actions = mimas_run(scenario, zc.mimas.get("implementors"))
            print(
                f"At the {_readable.get(scenario.event)} {dcid} ({dc_info['visit']} on {dc_info['beamLineName']}):"
            )
            for a in sorted(actions, key=lambda a: str(type(a)) + " " + a.recipe):
                try:
                    validate(a)
                except ValueError:
                    print(
                        f"Mimas scenario for dcid {dcid}, {scenario.event} returned invalid action {a!r}"
                    )
                    raise

                if isinstance(a, MimasRecipeInvocation):
                    if args.show_commands:
                        print(" - " + zocalo_command_line(a))
                    else:
                        print(f" - for dcid {a.dcid} call recipe {a.recipe}")
                elif isinstance(a, MimasISPyBJobInvocation):
                    full_recipe = f"ispyb-{a.recipe}"
                    if args.show_commands:
                        print(" - " + zocalo_command_line(a))
                    else:
                        print(
                            f" - create ISPyB job for dcid {a.dcid} named {a.displayname!r} with recipe '{full_recipe}' (autostart={a.autostart})"
                        )

                    triggers = get_recipe_triggers(
                        zc.storage.get("zocalo.recipe_directory"), full_recipe
                    )
                    if triggers:
                        print("   Then trigger: ")
                        for trigger in triggers:
                            print(
                                f"    - {trigger['target']}: {trigger['comment']} (autostart={a.autostart})"
                            )

                else:
                    raise RuntimeError(f"Encountered unknown action {a!r}")
            if not actions:
                print(" - do nothing")
            print()
