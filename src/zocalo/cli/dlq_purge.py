#
# zocalo.dlq_purge
#   Retrieve all dead letter queue messages from ActiveMQ and store them
#   in a temporary directory.
#

from __future__ import annotations

import argparse
import json
import pathlib
import queue
import re
import sys
import time
from datetime import datetime
from functools import partial

import workflows

import zocalo.configuration
from zocalo.util.rabbitmq import RabbitMQAPI


def run() -> None:
    zc = zocalo.configuration.from_file()
    zc.activate()
    parser = argparse.ArgumentParser(
        usage="zocalo.dlq_purge [options] [queue [queue ...]]"
    )

    parser.add_argument("-?", action="help", help=argparse.SUPPRESS)
    dlqprefix = "zocalo"
    parser.add_argument(
        "--wait",
        action="store",
        dest="wait",
        type=float,
        help="Wait this many seconds for incoming messages",
    )
    if zc.storage and zc.storage.get("zocalo.dlq.purge_location"):
        dlq_dump_path = zc.storage["zocalo.dlq.purge_location"]
    else:
        dlq_dump_path = "./DLQ"
    parser.add_argument(
        "--location",
        action="store",
        dest="location",
        type=str,
        default=dlq_dump_path,
        help=f"Where to write out DLQ message files (default: {dlq_dump_path})",
    )
    parser.add_argument(
        "queues",
        nargs="*",
        help="Queues to purge of dead letters. For RabbitMQ do not include the dlq. prefix in the queue names",
    )
    zc.add_command_line_options(parser)
    workflows.transport.add_command_line_options(parser, transport_argument=True)

    args = parser.parse_args(["--stomp-prfx=DLQ"] + sys.argv[1:])
    if args.transport == "PikaTransport":
        queues = ["dlq." + a for a in args.queues]
    else:
        queues = args.queues
    transport = workflows.transport.lookup(args.transport)()

    characterfilter = re.compile(r"[^a-zA-Z0-9._-]+", re.UNICODE)
    idlequeue: queue.Queue = queue.Queue()

    def receive_dlq_message(header: dict, message: dict, rabbitmq=False) -> None:
        idlequeue.put_nowait("start")
        if rabbitmq:
            msg_time = int(datetime.timestamp(header["x-death"][0]["time"])) * 1000
            header["x-death"][0]["time"] = datetime.timestamp(
                header["x-death"][0]["time"]
            )
        else:
            msg_time = int(header["timestamp"])
        timestamp = time.localtime(msg_time / 1000)
        millisec = msg_time % 1000
        filepath = pathlib.Path(args.location, time.strftime("%Y-%m-%d", timestamp))
        filepath.mkdir(parents=True, exist_ok=True)
        filename = filepath / (
            "msg-"
            + time.strftime("%Y%m%d-%H%M%S", timestamp)
            + f"-{millisec:03d}-"
            + characterfilter.sub("_", str(header["message-id"]))
        )

        dlqmsg = {
            "exported": {
                "date": time.strftime("%Y-%m-%d"),
                "time": time.strftime("%H:%M:%S"),
            },
            "header": header,
            "message": message,
        }

        with filename.open("w") as fh:
            json.dump(dlqmsg, fh, indent=2, sort_keys=True)
        print(
            f"Message {header['message-id']} ({time.strftime('%Y-%m-%d %H:%M:%S', timestamp)}) exported:\n  {filename}"
        )
        transport.ack(header)
        idlequeue.put_nowait("done")

    transport.connect()
    if not queues:
        if args.transport == "StompTransport":
            queues = [dlqprefix + ".>"]
        elif args.transport == "PikaTransport":
            rmq = RabbitMQAPI.from_zocalo_configuration(zc)
            queues = [q.name for q in rmq.queues() if q.name.startswith("dlq.")]
    for queue_ in queues:
        print("Looking for DLQ messages in " + queue_)
        transport.subscribe(
            queue_,
            partial(receive_dlq_message, rabbitmq=args.transport == "PikaTransport"),
            acknowledgement=True,
        )
    try:
        idlequeue.get(True, args.wait or 3)
        while True:
            idlequeue.get(True, args.wait or 0.1)
    except queue.Empty:
        print("Done.")
    transport.disconnect()
