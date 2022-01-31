from __future__ import annotations

import logging
import sys

import workflows.contrib.start_service

import zocalo.configuration.argparse
import zocalo.util


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
        # load configuration and initialize logging
        self._zc = zocalo.configuration.from_file()
        envs = self._zc.activate()
        self.use_live_infrastructure = ("live" in envs) or (
            "default" in envs
        )  # deprecated
        self.setup_logging()

        if not hasattr(self._zc, "graylog") or not self._zc.graylog:
            # Enable logging to graylog, deprecated
            zocalo.enable_graylog()

        if (
            self._zc.storage
            and self._zc.storage.get("zocalo.default_transport")
            in workflows.transport.get_known_transports()
        ):
            workflows.transport.default_transport = self._zc.storage[
                "zocalo.default_transport"
            ]

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
        self._zc.add_command_line_options(parser)
        self.log.debug("Launching %r", sys.argv)

    def on_parsing(self, options, args):
        if options.verbose:
            self.console.setLevel(logging.DEBUG)
        if options.debug:
            self.console.setLevel(logging.DEBUG)
            logging.getLogger("pika").setLevel(logging.INFO)
            logging.getLogger("stomp.py").setLevel(logging.DEBUG)
            logging.getLogger("workflows").setLevel(logging.DEBUG)
        self.options = options

    def before_frontend_construction(self, kwargs):
        kwargs["verbose_service"] = True
        kwargs["environment"] = kwargs.get("environment", {})
        kwargs["environment"]["live"] = self.use_live_infrastructure
        kwargs["environment"]["config"] = self._zc
        return kwargs

    def on_frontend_preparation(self, frontend):
        if self.options.service_restart:
            frontend.restart_service = True

        extended_status = zocalo.util.extended_status_dictionary()
        if self.options.tag:
            extended_status["tag"] = self.options.tag

        original_status_function = frontend.get_status

        def extend_status_wrapper():
            status = original_status_function()
            status.update(extended_status)
            return status

        frontend.get_status = extend_status_wrapper
