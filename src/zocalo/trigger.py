import logging
from typing import NamedTuple, Any, List
from abc import abstractmethod, ABC


logger = logging.getLogger(__name__)


class TriggerResponse(NamedTuple):
    success: bool
    return_value: Any


class Trigger(ABC):
    name = None

    _jobid = None
    _dcid = None

    def __init__(self, ispyb, rw, header, message, parameters, transaction):
        self._ispyb = ispyb
        self._rw = rw
        self._parameters = parameters
        self._dcid = parameters("dcid")

    @property
    def parameters(self):
        return self._parameters

    @abstractmethod
    def run(self) -> TriggerResponse:
        pass

    def _add_job(self, display_name: str, recipe: str) -> int:
        """Create an ISPyB ProcessingJob"""
        jp = self._ispyb.mx_processing.get_job_params()
        jp["automatic"] = bool(self.parameters("automatic"))
        jp["comments"] = self.parameters("comment")
        jp["datacollectionid"] = self._dcid
        jp["display_name"] = display_name
        jp["recipe"] = recipe
        return self._ispyb.mx_processing.upsert_job(list(jp.values()))

    def _add_image_sweep(self, dcid: int, start_image: int, end_image: int) -> int:
        """Create an ISPyB ProcessingJobImageSweep"""
        if not self._jobid:
            logger.error("No jobid defined")
            return

        jisp = self._ispyb.mx_processing.get_job_image_sweep_params()
        jisp["datacollectionid"] = dcid
        jisp["start_image"] = start_image
        jisp["end_image"] = end_image
        jisp["job_id"] = self._jobid
        return self._ispyb.mx_processing.upsert_job_image_sweep(list(jisp.values()))

    def _add_parameters(self, params: dict) -> List[int]:
        """Add ISPyB ProcessingJobParameters"""
        if not self._jobid:
            logger.error("No jobid defined")
            return

        jppids = []
        for key, value in params.items():
            jpp = self._ispyb.mx_processing.get_job_parameter_params()
            jpp["job_id"] = self._jobid
            jpp["parameter_key"] = key
            jpp["parameter_value"] = value
            jppids.append(
                self._ispyb.mx_processing.upsert_job_parameter(list(jpp.values()))
            )

        return jppids

    def _trigger_job(self, parameters={}):
        """Trigger a recipe with an ISPyB ProcessingJob id"""
        message = {"recipes": [], "parameters": {"ispyb_process": self._jobid}}
        message["parameters"].update(parameters)
        self._rw.transport.send("processing_recipe", message)
