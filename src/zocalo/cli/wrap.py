#
# zocalo.wrap
#   Wraps a command so that its status can be tracked in zocalo
#


import json
import logging
import os
import sys
from optparse import SUPPRESS_HELP, OptionParser

import pkg_resources
import workflows
import workflows.recipe.wrapper
import workflows.services.common_service
import workflows.transport
import workflows.util

import zocalo.configuration
import zocalo.wrapper


def run():
    cmdline_args = sys.argv[1:]
    # Enable logging to console
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger("workflows").setLevel(logging.INFO)
    logging.getLogger("zocalo").setLevel(logging.INFO)
    logging.getLogger().setLevel(logging.WARN)
    logging.getLogger().addHandler(console)
    log = logging.getLogger("dlstbx.wrap")

    zc = zocalo.configuration.from_file()
    if "--test" in cmdline_args:
        if "test" in zc.environments:
            zc.activate_environment("test")
    else:
        if "live" in zc.environments:
            zc.activate_environment("live")

    known_wrappers = {
        e.name: e.load for e in pkg_resources.iter_entry_points("zocalo.wrappers")
    }

    # Set up parser
    parser = OptionParser(usage="zocalo.wrap [options]")
    parser.add_option("-?", action="help", help=SUPPRESS_HELP)

    parser.add_option(
        "--wrap",
        action="store",
        dest="wrapper",
        type="choice",
        metavar="WRAP",
        default=None,
        choices=list(known_wrappers),
        help="Object to be wrapped (valid choices: %s)" % ", ".join(known_wrappers),
    )
    parser.add_option(
        "--recipewrapper",
        action="store",
        dest="recipewrapper",
        metavar="RW",
        default=None,
        help="A serialized recipe wrapper file " "for downstream communication",
    )

    parser.add_option(
        "--test", action="store_true", help="Run in ActiveMQ testing namespace (zocdev)"
    )
    parser.add_option(
        "--live",
        action="store_true",
        help="Run in ActiveMQ live namespace (zocalo, default)",
    )

    parser.add_option(
        "-t",
        "--transport",
        dest="transport",
        metavar="TRN",
        default="StompTransport",
        help="Transport mechanism. Known mechanisms: "
        + ", ".join(workflows.transport.get_known_transports())
        + " (default: %default)",
    )
    parser.add_option(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="Show debug level messages",
    )
    workflows.transport.add_command_line_options(parser)

    # Parse command line arguments
    (options, args) = parser.parse_args()

    if not cmdline_args:
        parser.print_help()
        sys.exit()

    # Instantiate specific wrapper
    if not options.wrapper:
        sys.exit("A wrapper object must be specified.")

    if options.verbose:
        console.setLevel(logging.DEBUG)

    log.info(
        "Starting wrapper for %s with recipewrapper file %s",
        options.wrapper,
        options.recipewrapper,
    )

    # Connect to transport and start sending notifications
    transport = workflows.transport.lookup(options.transport)()
    transport.connect()
    st = zocalo.wrapper.StatusNotifications(transport.broadcast_status, options.wrapper)
    for env in ("SGE_CELL", "JOB_ID"):
        if env in os.environ:
            st.set_static_status_field("cluster_" + env, os.getenv(env))

    # Instantiate chosen wrapper
    instance = known_wrappers[options.wrapper]()()
    instance.status_thread = st

    # If specified, read in a serialized recipewrapper
    if options.recipewrapper:
        with open(options.recipewrapper) as fh:
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
