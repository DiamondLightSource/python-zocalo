# zocalo.service defaults to running in the testing ActiveMQ namespace (zocdev),
# rather than the live namespace (zocalo).
# This is to stop servers started by developers on their machines accidentally
# interfering with live data processing.
# To run a live server you must specify '--live'


import logging
import os
import sys

import workflows
import workflows.contrib.start_service
from workflows.transport.stomp_transport import StompTransport

import zocalo
import zocalo.configuration


def start_service():
    ServiceStarter().run(
        program_name="zocalo.service",
        version=zocalo.__version__,
        transport_command_channel="command",
    )


class ServiceStarter(workflows.contrib.start_service.ServiceStarter):
    """Starts a workflow service"""

    __frontendref = None

    def setup_logging(self):
        """Initialize common logging framework. Everything is logged to central
        graylog server. Depending on setting messages of DEBUG or INFO and higher
        go to console."""
        logger = logging.getLogger()
        logger.setLevel(logging.WARN)

        # Enable logging to console
        try:
            from dlstbx.util.colorstreamhandler import ColorStreamHandler

            self.console = ColorStreamHandler()
        except ImportError:
            self.console = logging.StreamHandler()
        self.console.setLevel(logging.INFO)
        logger.addHandler(self.console)

        logging.getLogger("workflows").setLevel(logging.INFO)
        logging.getLogger("zocalo").setLevel(logging.DEBUG)

        self.log = logging.getLogger("zocalo.service")
        self.log.setLevel(logging.DEBUG)

    def __init__(self):
        # initialize logging
        self._zc = zocalo.configuration.from_file()

        # change settings when in live mode
        default_configuration = "/dls_sw/apps/zocalo/secrets/credentials-testing.cfg"
        if "--live" in sys.argv:
            self.use_live_infrastructure = True
            default_configuration = "/dls_sw/apps/zocalo/secrets/credentials-live.cfg"
            if "live" in self._zc.environments:
                self._zc.activate_environment("live")
        else:
            self.use_live_infrastructure = False
        self.setup_logging()

        if not hasattr(self._zc, "graylog") or not self._zc.graylog:
            # Enable logging to graylog, obsolete
            zocalo.enable_graylog()

        if os.path.exists(default_configuration):
            StompTransport.load_configuration_file(default_configuration)

    def on_parser_preparation(self, parser):
        parser.add_option(
            "-v",
            "--verbose",
            action="store_true",
            dest="verbose",
            default=False,
            help="Show debug output",
        )
        parser.add_option(
            "--tag",
            dest="tag",
            metavar="TAG",
            default=None,
            help="Individual tag related to this service instance",
        )
        parser.add_option(
            "-d",
            "--debug",
            action="store_true",
            dest="debug",
            default=False,
            help="Set debug log level for workflows",
        )
        parser.add_option(
            "-r",
            "--restart",
            action="store_true",
            dest="service_restart",
            default=False,
            help="Restart service on failure",
        )
        parser.add_option(
            "--test",
            action="store_true",
            dest="test",
            help="Run in ActiveMQ testing namespace (zocdev, default)",
        )
        parser.add_option(
            "--live",
            action="store_true",
            dest="test",
            help="Run in ActiveMQ live namespace (zocalo)",
        )
        self.log.debug("Launching " + str(sys.argv))

    def on_parsing(self, options, args):
        if options.verbose:
            self.console.setLevel(logging.DEBUG)
        if options.debug:
            self.console.setLevel(logging.DEBUG)
            logging.getLogger("stomp.py").setLevel(logging.DEBUG)
            logging.getLogger("workflows").setLevel(logging.DEBUG)
        self.options = options

    def before_frontend_construction(self, kwargs):
        kwargs["verbose_service"] = True
        kwargs["environment"] = kwargs.get("environment", {})
        kwargs["environment"]["live"] = self.use_live_infrastructure
        return kwargs

    def on_frontend_preparation(self, frontend):
        if self.options.service_restart:
            frontend.restart_service = True

        extended_status = {"zocalo": zocalo.__version__}
        if self.options.tag:
            extended_status["tag"] = self.options.tag
        for env in ("SGE_CELL", "JOB_ID"):
            if env in os.environ:
                extended_status["cluster_" + env] = os.environ[env]

        original_status_function = frontend.get_status

        def extend_status_wrapper():
            status = original_status_function()
            status.update(extended_status)
            return status

        frontend.get_status = extend_status_wrapper
