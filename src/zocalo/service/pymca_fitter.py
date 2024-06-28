from __future__ import absolute_import, annotations, division, print_function

import workflows.recipe
from workflows.services.common_service import CommonService

from zocalo.util.pymca_fitter import plot_fluorescence_spectrum

PARAMETERS = [
    "inputFile",
    "omega",
    "transmission",
    "samplexyz",
    "acqTime",
    "energy",
]


class DLSPyMcaFitter(CommonService):
    """A service that takes an XRF dataset and sends it to PyMca for fitting"""

    _service_name = "DLS PyMca Fitter"

    _logger_name = "dlstbx.services.pymca_fitter"

    def initializing(self):
        """Subscribe to a queue. Received messages must be acknowledged."""
        self.log.info("PyMca fitter service starting")
        workflows.recipe.wrap_subscribe(
            self._transport,
            "pymca.fitter",
            self.pymca_fitter_call,
            acknowledgement=True,
            log_extender=self.extend_log,
        )

    def pymca_fitter_call(self, rw, header, message):
        """Call dispatcher"""
        args = [rw.recipe_step.get("parameters", {}).get(param) for param in PARAMETERS]

        self.log.debug("Commands: %s", " ".join(args))
        try:
            plot_fluorescence_spectrum(*args)
        except Exception as e:
            self.log.warning(f"Error running PyMca: {e}", exc_info=True)
            rw.transport.ack(header)
            return
        self.log.info(
            "%s was successfully processed",
            rw.recipe_step.get("parameters", {}).get("inputFile"),
        )
        rw.transport.ack(header)
