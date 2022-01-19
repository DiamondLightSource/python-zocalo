#
# zocalo.dlq_reinject
#   Take a dead letter queue message from a file and send it back to its queue
#   for a retry.
#
from __future__ import annotations

import argparse
import json
import os
import re
import select
import sys
import time
from pprint import pprint

import workflows.transport

import zocalo.configuration
from zocalo.util.rabbitmq import RabbitMQAPI


def run() -> None:
    zc = zocalo.configuration.from_file()
    zc.activate()
    parser = argparse.ArgumentParser(
        usage="zocalo.dlq_reinject [options] file [file [..]]"
    )

    parser.add_argument("-?", action="help", help=argparse.SUPPRESS)
    parser.add_argument(
        "-r",
        "--remove",
        action="store_true",
        default=False,
        dest="remove",
        help="Delete file on successful reinjection",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        dest="verbose",
        help="Show message contents",
    )
    parser.add_argument(
        "-d",
        "--destination",
        action="store",
        default=None,
        dest="destination_override",
        help="Reinject messages to a different destination. Any name given must include the stomp prefix.",
    )
    parser.add_argument(
        "-w",
        "--wait",
        default=None,
        dest="wait",
        help="Wait this many seconds between reinjections",
    )
    parser.add_argument(
        "files", nargs="*", help="File(s) containing DLQ messages to be reinjected"
    )

    zc.add_command_line_options(parser)
    workflows.transport.add_command_line_options(parser, transport_argument=True)
    args = parser.parse_args()
    transport = workflows.transport.lookup(args.transport)()

    stdin = []
    try:
        stdin_fileno = getattr(sys.stdin, "fileno", lambda: None)()
    except Exception:
        stdin_fileno = None
    if isinstance(stdin_fileno, int) and select.select([sys.stdin], [], [], 0.0)[0]:
        dlq_purge_filename_format = re.compile(r"^  \/")
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            if dlq_purge_filename_format.match(line):
                stdin.append(line.strip())
        print(f"{len(stdin)} filenames read from stdin")

    if not stdin and not args.files:
        sys.exit("No DLQ message files given.")

    transport.connect()

    first = True
    for dlqfile in args.files + stdin:
        if not os.path.exists(dlqfile):
            print(f"Ignoring missing file {dlqfile}")
            continue
        if not first and args.wait:
            time.sleep(float(args.wait))
        first = False
        with open(dlqfile) as fh:
            dlqmsg = json.load(fh)
        print(f"Parsing message from {dlqfile}")
        if (
            not isinstance(dlqmsg, dict)
            or not dlqmsg.get("header")
            or not dlqmsg.get("message")
        ):
            sys.exit("File is not a valid DLQ message.")
        if args.verbose:
            pprint(dlqmsg)

        if args.transport == "StompTransport":
            destination = (
                dlqmsg["header"]
                .get("original-destination", dlqmsg["header"]["destination"])
                .split("/", 2)
            )
            if destination[1] == "queue":
                print("sending...")
                send_function = transport.send
            elif destination[1] == "topic":
                print("broadcasting...")
                send_function = transport.broadcast
            else:
                sys.exit("Cannot process message, unknown message mechanism")
            if args.destination_override:
                destination[2] = args.destination_override
            header = dlqmsg["header"]
            for drop_field in (
                "content-length",
                "destination",
                "expires",
                "message-id",
                "original-destination",
                "originalExpiration",
                "subscription",
                "timestamp",
                "redelivered",
            ):
                if drop_field in header:
                    del header[drop_field]
            header["dlq-reinjected"] = "True"
            send_function(
                destination[2], dlqmsg["message"], headers=header, ignore_namespace=True
            )
        elif args.transport == "PikaTransport":
            print("pika transport detected")
            header = dlqmsg["header"]
            header["dlq-reinjected"] = "True"
            exchange = header.get("x-death", [{}])[0].get("exchange")
            if exchange:
                rmqapi = RabbitMQAPI.from_zocalo_configuration(zc)
                exchange_info = rmqapi.get("queues").json()
                for exch in exchange_info:
                    if exch["name"] == exchange:
                        if exch["type"] == "fanout":
                            transport.broadcast(
                                args.destination_override or destination,
                                dlqmsg["message"],
                                headers=_rabbit_prepare_header(header),
                            )
            else:
                destination = header.get("x-death", [{}])[0].get("queue")
                transport.send(
                    args.destination_override or destination,
                    dlqmsg["message"],
                    headers=_rabbit_prepare_header(header),
                )
        if args.remove:
            os.remove(dlqfile)
        print("Done.\n")

    transport.disconnect()


def _rabbit_prepare_header(header: dict) -> dict:
    drop = {
        "message-id",
        "routing_key",
        "redelivered",
        "exchange",
        "consumer_tag",
        "delivery_mode",
    }
    return {k: str(v) for k, v in header.items() if k not in drop}
