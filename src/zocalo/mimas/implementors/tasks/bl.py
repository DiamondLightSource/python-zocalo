from zocalo.mimas.tasks import Tasks
from zocalo.mimas.classes import (
    MimasExperimentType,
    MimasRecipeInvocation,
    MimasISPyBJobInvocation,
    MimasEvent,
)


class bl(Tasks):
    beamline = "bl"

    def run(self, scenario):
        tasks = []

        if scenario.event == MimasEvent.START:
            if scenario.experimenttype == MimasExperimentType.ENERGY_SCAN:
                tasks.append(
                    MimasRecipeInvocation(dcid=scenario.dcid, recipe="exafs-qa")
                )

        if scenario.event == MimasEvent.END:
            if scenario.experimenttype == MimasExperimentType.XRF_MAP:
                tasks.append(
                    MimasISPyBJobInvocation(
                        dcid=scenario.dcid,
                        autostart=True,
                        displayname="PyMCA Fitter",
                        recipe="pymca",
                        source="automatic",
                    )
                )

        return tasks
