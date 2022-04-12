#
# zocalo.wrap
#   Wraps a command so that its status can be tracked in zocalo
#

from __future__ import annotations

import argparse
import faulthandler
import json
import logging
import signal
import sys

import pkg_resources
import workflows.recipe.wrapper
import workflows.services.common_service
import workflows.transport
import workflows.util

import zocalo.configuration.argparse
import zocalo.util
import zocalo.wrapper


def _enable_faulthandler():
    """Display a traceback on crashing with non-Python errors, such as
    segmentation faults, and when the process is signalled with SIGUSR2
    (not available on Windows)"""
    # Ignore errors during setup; SIGUSR2 not available on Windows, and
    # the attached STDERR might not support what faulthandler wants
    try:
        faulthandler.enable()
        faulthandler.register(signal.SIGUSR2)
    except Exception:
        pass


def run():
    zc = zocalo.configuration.from_file()
    zc.activate()

    known_wrappers = {
        e.name: e.load for e in pkg_resources.iter_entry_points("zocalo.wrappers")
    }

    # Set up parser
    parser = argparse.ArgumentParser(usage="zocalo.wrap [options]")
    parser.add_argument("-?", action="help", help=argparse.SUPPRESS)

    parser.add_argument(
        "--wrap",
        action="store",
        dest="wrapper",
        metavar="WRAP",
        default=None,
        choices=list(known_wrappers),
        help="Object to be wrapped (valid choices: %s)" % ", ".join(known_wrappers),
    )
    parser.add_argument(
        "--recipewrapper",
        action="store",
        dest="recipewrapper",
        metavar="RW",
        default=None,
        help="A serialized recipe wrapper file for downstream communication",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output verbosity",
    )

    zc.add_command_line_options(parser)
    workflows.transport.add_command_line_options(parser, transport_argument=True)

    # Parse command line arguments
    args = parser.parse_args()

    # Always enable logging to console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)
    if args.verbose:
        console.setLevel(logging.DEBUG)

    if zc.logging:
        zc.logging.verbosity = args.verbose
    else:
        logging.getLogger("workflows").setLevel(logging.INFO)
        logging.getLogger("zocalo").setLevel(logging.INFO)
        logging.getLogger().setLevel(logging.WARN)

    _enable_faulthandler()
    log = logging.getLogger("zocalo.wrap")

    # Instantiate specific wrapper
    if not args.wrapper:
        sys.exit("A wrapper object must be specified.")

    log.info(
        "Starting wrapper for %s with recipewrapper file %s",
        args.wrapper,
        args.recipewrapper,
    )

    # Connect to transport and start sending notifications
    transport = workflows.transport.lookup(args.transport)()
    transport.connect()
    st = zocalo.wrapper.StatusNotifications(transport.broadcast_status, args.wrapper)
    for field, value in zocalo.util.extended_status_dictionary().items():
        st.set_static_status_field(field, value)

    # Instantiate chosen wrapper
    instance = known_wrappers[args.wrapper]()()
    instance.status_thread = st

    # If specified, read in a serialized recipewrapper
    if args.recipewrapper:
        with open(args.recipewrapper) as fh:
            recwrap = workflows.recipe.wrapper.RecipeWrapper(
                message=json.load(fh), transport=transport
            )
        instance.set_recipe_wrapper(recwrap)

        if zc.graylog and recwrap.environment.get("ID"):
            # If recipe ID available then include that in all future log messages
            class ContextFilter(logging.Filter):
                def filter(self, record):
                    record.recipe_ID = recwrap.environment["ID"]
                    return True

            zc.graylog.addFilter(ContextFilter())

        if recwrap.recipe_step.get("wrapper", {}).get("task_information"):
            # If the recipe contains an extra task_information field then add this to the status display
            st.taskname += (
                " (" + str(recwrap.recipe_step["wrapper"]["task_information"]) + ")"
            )

    instance.prepare("Starting processing")

    st.set_status(workflows.services.common_service.Status.PROCESSING)
    log.info("Setup complete, starting processing")

    try:
        if instance.run():
            log.info("successfully finished processing")
            instance.success("Finished processing")
        else:
            log.info("processing failed")
            instance.failure("Processing failed")
        st.set_status(workflows.services.common_service.Status.END)
    except KeyboardInterrupt:
        log.info("Shutdown via Ctrl+C")
        st.set_status(workflows.services.common_service.Status.END)
    except Exception as e:
        log.error(str(e), exc_info=True)
        instance.failure(e)
        st.set_status(workflows.services.common_service.Status.ERROR)

    instance.done("Finished processing")

    st.shutdown()
    st.join()
    log.debug("Terminating")
    transport.disconnect()
