#
# zocalo.go
#   Process a datacollection
#

from __future__ import annotations

import argparse
import getpass
import json
import pathlib
import socket
import sys
import uuid
from pprint import pprint

import workflows.recipe
import workflows.transport

import zocalo.configuration.argparse

# Example: zocalo.go -r example-xia2 527189


def run():
    zc = zocalo.configuration.from_file()
    zc.activate()

    parser = argparse.ArgumentParser(
        usage="zocalo.go [options] dcid",
        description="Triggers processing of a standard "
        "recipe, of an arbitrary recipe from a local file, or of an entry in "
        "the ISPyB processing table.",
    )

    parser.add_argument("-?", action="help", help=argparse.SUPPRESS)
    parser.add_argument(
        "-r",
        "--recipe",
        dest="recipe",
        metavar="RCP",
        action="append",
        default=[],
        help="Name of a recipe to run. Can be used multiple times. "
        "Recipe names correspond to filenames (excluding .json) in /dls_sw/apps/zocalo/live/recipes",
    )
    parser.add_argument(
        "-a",
        "--autoprocscalingid",
        dest="autoprocscalingid",
        metavar="APSID",
        action="store",
        type=str,
        default=None,
        help="An auto processing scaling ID for downstream processing recipes.",
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="recipefile",
        metavar="FILE",
        action="store",
        type=str,
        default="",
        help="Run recipe contained in this file.",
    )
    parser.add_argument(
        "-n",
        "--no-dcid",
        dest="nodcid",
        action="store_true",
        default=False,
        help="Trigger recipe without specifying a data collection ID",
    )
    parser.add_argument(
        "--drop",
        dest="dropfile",
        action="store_true",
        default=False,
        help=argparse.SUPPRESS,
    )  # Write directly to file, do not attempt to send as message
    parser.add_argument(
        "-p",
        "--reprocessing",
        dest="reprocess",
        action="store_true",
        default=False,
        help="Means a reprocessing ID is given rather than a data collection ID",
    )
    parser.add_argument(
        "-s",
        "--set",
        dest="parameters",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Set an additional variable for recipe evaluation",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="Show raw message before sending",
    )
    parser.add_argument(
        "--dry-run",
        dest="dryrun",
        action="store_true",
        default=False,
        help="Verify that everything is in place that the message could be sent, but don't actually send the message",
    )
    parser.add_argument(
        "dcid", nargs="*", help="Data collection ID of required processing"
    )

    zc.add_command_line_options(parser)
    workflows.transport.add_command_line_options(parser, transport_argument=True)
    args = parser.parse_args()

    if zc.storage and zc.storage.get("zocalo.go.fallback_location"):
        dropfile_fallback = pathlib.Path(zc.storage["zocalo.go.fallback_location"])
    else:
        dropfile_fallback = False

    def write_message_to_dropfile(message, headers):
        message_serialized = (
            json.dumps({"headers": headers, "message": message}, indent=2) + "\n"
        )

        fallback = dropfile_fallback / str(uuid.uuid4())
        if args.dryrun:
            print("Not storing message in %s (running with --dry-run)" % fallback)
            return
        fallback.write_text(message_serialized)
        print("Message successfully stored in %s" % fallback)

    def send_or_defer(message):
        headers = {
            "zocalo.go.user": getpass.getuser(),
            "zocalo.go.host": socket.gethostname(),
        }
        if args.verbose:
            pprint(message)
        if dropfile_fallback and args.dropfile:
            return write_message_to_dropfile(message, headers)
        try:
            transport = workflows.transport.lookup(args.transport)()
            if args.dryrun:
                print("Not sending message (running with --dry-run)")
                return
            transport.connect()
            transport.send("processing_recipe", message, headers=headers)
            transport.disconnect()
        except (
            KeyboardInterrupt,
            SyntaxError,
            AssertionError,
            AttributeError,
            ImportError,
            TypeError,
            ValueError,
        ):
            raise
        except Exception:
            if not dropfile_fallback:
                raise
            print("\n\n")
            import traceback

            traceback.print_exc()
            print("\n\nAttempting to store message in fallback location")
            write_message_to_dropfile(message, headers)

    message = {"recipes": args.recipe, "parameters": {}}
    for kv in args.parameters:
        if "=" not in kv:
            sys.exit(f"Invalid variable specification '{kv}'")
        key, value = kv.split("=", 1)
        message["parameters"][key] = value

    if (
        not args.recipe
        and not args.recipefile
        and not args.nodcid
        and not args.reprocess
    ):
        sys.exit("No recipes specified.")

    if args.recipefile:
        with open(args.recipefile) as fh:
            custom_recipe = workflows.recipe.Recipe(json.load(fh))
        custom_recipe.validate()
        message["custom_recipe"] = custom_recipe.recipe

    if args.nodcid:
        if args.recipe:
            print("Running recipes", args.recipe)
        if args.recipefile:
            print("Running recipe from file", args.recipefile)
        print("without specified data collection.")
        send_or_defer(message)
        print("\nSubmitted.")
        sys.exit(0)

    if len(args.dcid) > 1:
        sys.exit("Only a single data collection ID can be specified.")
    if not args.dcid:
        sys.exit("You must either specify a data collection ID or option --no-dcid.")

    dcid = int(args.dcid[0])
    assert dcid > 0, "Invalid data collection ID given."

    if args.reprocess:
        # Given ID is a reprocessing ID. Nothing else needs to be specified.
        if args.recipe:
            print("Running recipes", args.recipe)
        message["parameters"]["ispyb_process"] = dcid
        send_or_defer(message)
        print("\nReprocessing task submitted for ID %d." % dcid)
        sys.exit(0)

    if message["recipes"]:
        print("Running recipes", message["recipes"])

    if args.recipefile:
        print("Running recipe from file", args.recipefile)

    if not message["recipes"] and not message.get("custom_recipe"):
        sys.exit("No recipes specified.")
    print("for data collection", dcid)
    message["parameters"]["ispyb_dcid"] = dcid

    if args.autoprocscalingid:
        apsid = int(args.autoprocscalingid)
        assert apsid > 0, "Invalid auto processing scaling ID given."
        message["parameters"]["ispyb_autoprocscalingid"] = apsid

    send_or_defer(message)
    print("\nSubmitted.")
