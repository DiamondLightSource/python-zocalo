import workflows.recipe
from workflows.services.common_service import CommonService

from zocalo.mimas.core import run
from zocalo.mimas.classes import (
    MimasEvent,
    MimasExperimentType,
    MimasRunStatus,
    MimasDCClass,
    MimasISPyBSweep,
    MimasISPyBUnitCell,
    MimasISPyBSpaceGroup,
    MimasDetectorClass,
    MimasScenario,
    MimasRecipeInvocation,
    MimasISPyBJobInvocation,
    validate,
    zocalo_message,
)


class Mimas(CommonService):
    """
    Business logic component. Given a data collection id and some description
    of event circumstances (beamline, experiment description, start or end of
    scan) this service decides what recipes should be run with what settings.
    """

    # Human readable service name
    _service_name = "Mimas"

    # Logger name
    _logger_name = "zocalo.services.mimas"

    def initializing(self):
        """Subscribe to the mimas queue. Received messages must be acknowledged."""
        self.log.info("Mimas starting")

        workflows.recipe.wrap_subscribe(
            self._transport,
            "mimas",
            self.process,
            acknowledgement=True,
            log_extender=self.extend_log,
        )

    def _extract_scenario(self, step):
        dcid = step.get("dcid")
        if not dcid or not dcid.isnumeric():
            return f"Invalid Mimas request rejected (dcid = {dcid!r})"

        event = step.get("event")
        if not isinstance(event, str):
            event = repr(event)
        try:
            event = MimasEvent[event.upper()]
        except KeyError:
            return f"Invalid Mimas request rejected (Event = {event!r})"

        experimenttype = step.get("experimenttype")
        if not experimenttype or not isinstance(experimenttype, str):
            return (
                f"Invalid Mimas request rejected (experimenttype = {experimenttype!r})"
            )

        try:
            experimenttype_safe = experimenttype.replace(" ", "_")
            experimenttype_mimas = MimasExperimentType[experimenttype_safe.upper()]
        except KeyError:
            self.log.warning(
                f"Invalid Mimas request (Experiment type = {experimenttype!r})"
            )
            experimenttype_mimas = MimasExperimentType.UNDEFINED

        dc_class = step.get("dc_class")
        if isinstance(dc_class, dict):
            # legacy format
            if dc_class["grid"]:
                dc_class_mimas = MimasDCClass.GRIDSCAN
            elif dc_class["screen"]:
                dc_class_mimas = MimasDCClass.SCREENING
            elif dc_class["rotation"]:
                dc_class_mimas = MimasDCClass.ROTATION
            else:
                dc_class_mimas = MimasDCClass.UNDEFINED
        else:
            try:
                dc_class_mimas = MimasDCClass[dc_class.upper()]
            except (KeyError, AttributeError):
                self.log.warning(
                    f"Invalid Mimas request (Data collection class = {dc_class!r})"
                )
                dc_class_mimas = MimasDCClass.UNDEFINED

        run_status = step.get("run_status").lower()
        if "success" in run_status:
            run_status_mimas = MimasRunStatus.SUCCESS
        elif "fail" in run_status:
            run_status_mimas = MimasRunStatus.FAILURE
        else:
            run_status_mimas = MimasRunStatus.UNKNOWN

        sweep_list = tuple(
            MimasISPyBSweep(*info) for info in (step.get("sweep_list") or [])
        )

        cell = step.get("unit_cell")
        if cell:
            cell = MimasISPyBUnitCell(*cell)
        else:
            cell = None

        spacegroup = step.get("space_group")
        if spacegroup:
            spacegroup = MimasISPyBSpaceGroup(spacegroup)
            self.log.info(spacegroup)
            try:
                validate(spacegroup)
            except ValueError:
                self.log.warning(
                    f"Invalid spacegroup for dcid {dcid}: {spacegroup}", exc_info=True
                )
                spacegroup = None
        else:
            spacegroup = None

        detectorclass = {
            "eiger": MimasDetectorClass.EIGER,
            "pilatus": MimasDetectorClass.PILATUS,
        }.get(step.get("detectorclass", "").lower())

        return MimasScenario(
            dcid=int(dcid),
            experimenttype=experimenttype_mimas,
            dcclass=dc_class_mimas,
            event=event,
            beamline=step.get("beamline"),
            proposalcode=step.get("proposalcode"),
            runstatus=run_status_mimas,
            spacegroup=spacegroup,
            unitcell=cell,
            getsweepslistfromsamedcg=sweep_list,
            preferred_processing=step.get("preferred_processing"),
            detectorclass=detectorclass,
        )

    def process(self, rw, header, message):
        """Process an incoming event."""

        # Pass incoming event information into Mimas scenario object
        scenario = self._extract_scenario(rw.recipe_step["parameters"])
        if isinstance(scenario, str):
            self.log.error(scenario)
            rw.transport.nack(header)
            return

        # Validate scenario
        try:
            validate(scenario, expectedtype=MimasScenario)
        except ValueError:
            self.log.error("Invalid Mimas request rejected", exc_info=True)
            rw.transport.nack(header)
            return

        txn = rw.transport.transaction_begin()
        rw.set_default_channel("dispatcher")

        self.log.debug("Evaluating %r", scenario)
        things_to_do = run(scenario, self.config.mimas.get("implementors"))

        passthrough = rw.recipe_step.get("passthrough", {})
        for ttd in things_to_do:
            try:
                validate(
                    ttd, expectedtype=(MimasRecipeInvocation, MimasISPyBJobInvocation),
                )
            except ValueError:
                self.log.error("Invalid Mimas response detected", exc_info=True)
                rw.transport.nack(header)
                rw.transport.transaction_abort(txn)
                return

            self.log.info("Running: %r", ttd)
            try:
                ttd_zocalo = zocalo_message(ttd)
            except ValueError:
                self.log.error(f"Error zocalizing Mimas object {ttd!r}", exc_info=True)
                rw.transport.nack(header)
                rw.transport.transaction_abort(txn)
                return

            if passthrough:
                if isinstance(ttd, MimasRecipeInvocation):
                    for param, value in passthrough.items():
                        ttd_zocalo["parameters"][param] = value
                else:
                    # TODO: Must be a better way to deal with this
                    ttd_zocalo["triggervariables"] = list(
                        ttd_zocalo["triggervariables"]
                    )
                    for param, value in passthrough.items():
                        ttd_zocalo["triggervariables"].append(
                            {"key": param, "value": value}
                        )
                    ttd_zocalo["triggervariables"] = tuple(
                        ttd_zocalo["triggervariables"]
                    )

            if isinstance(ttd, MimasRecipeInvocation):
                rw.send(ttd_zocalo, transaction=txn)
            else:
                rw.send_to("ispyb", ttd_zocalo, transaction=txn)

        rw.transport.ack(header, transaction=txn)
        rw.transport.transaction_commit(txn)
