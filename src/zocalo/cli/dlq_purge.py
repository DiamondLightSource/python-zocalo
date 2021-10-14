#
# zocalo.dlq_purge
#   Retrieve all dead letter queue messages from ActiveMQ and store them
#   in a temporary directory.
#


import argparse
import errno
import json
import os
import queue
import re
import sys
import time
from datetime import datetime
from functools import partial

import workflows

import zocalo.configuration


def run() -> None:
    zc = zocalo.configuration.from_file()
    zc.activate()
    parser = argparse.ArgumentParser(
        usage="dlstbx.dlq_purge [options] [queue [queue ...]]"
    )

    parser.add_argument("-?", action="help", help=argparse.SUPPRESS)
    dlqprefix = "zocalo"
    # override default stomp host
    parser.add_argument(
        "--wait",
        action="store",
        dest="wait",
        type=float,
        help="Wait this many seconds for ActiveMQ replies",
    )
    parser.add_argument(
        "queues",
        nargs="*",
        help="Queues to purge of dead letters. For RabbitMQ do not include the dlq. prefix in the queue names",
    )
    zc.add_command_line_options(parser)
    workflows.transport.add_command_line_options(parser, transport_argument=True)
    print(sys.argv)
    args = parser.parse_args(["--stomp-prfx=DLQ"] + sys.argv[1:])
    if args.transport == "PikaTransport":
        queues = ["dlq." + a for a in args.queues]
    else:
        queues = args.queues
    transport = workflows.transport.lookup(args.transport)()

    if zc.storage and zc.storage.get("zocalo.dlq.purge_location"):
        dlq_dump_path = zc.storage["zocalo.dlq.purge_location"]
    else:
        dlq_dump_path = "./DLQ"

    characterfilter = re.compile(r"[^a-zA-Z0-9._-]+", re.UNICODE)
    idlequeue: queue.Queue = queue.Queue()

    def receive_dlq_message(header: dict, message: dict, rabbitmq=False) -> None:
        idlequeue.put_nowait("start")
        if rabbitmq:
            msg_time = (
                int(datetime.timestamp(header["headers"]["x-death"][0]["time"])) * 1000
            )
            header["headers"]["x-death"][0]["time"] = datetime.timestamp(
                header["headers"]["x-death"][0]["time"]
            )
        else:
            msg_time = int(header["timestamp"])
        timestamp = time.localtime(msg_time / 1000)
        millisec = msg_time % 1000
        filepath = os.path.join(
            dlq_dump_path,
            time.strftime("%Y-%m-%d", timestamp),
            #       time.strftime('%H-%M', timestamp),
        )
        filename = (
            "msg-"
            + time.strftime("%Y%m%d-%H%M%S", timestamp)
            + "-"
            + "%03d" % millisec
            + "-"
            + characterfilter.sub("_", str(header["message-id"]))
        )
        try:
            os.makedirs(filepath)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(filepath):
                pass
            else:
                raise

        dlqmsg = {
            "exported": {
                "date": time.strftime("%Y-%m-%d"),
                "time": time.strftime("%H:%M:%S"),
            },
            "header": header,
            "message": message,
        }

        with open(os.path.join(filepath, filename), "w") as fh:
            fh.write(json.dumps(dlqmsg, indent=2, sort_keys=True))
        print(
            f"Message {header['message-id']} ({time.strftime('%Y-%m-%d %H:%M:%S', timestamp)}) exported:\n {os.path.join(filepath, filename)}"
        )
        if rabbitmq:
            # subscription_id does nothing for RabbitMQ but it is currently required by workflows
            transport.ack(header, subscription_id=header["message-id"])
        else:
            transport.ack(header)
        idlequeue.put_nowait("done")

    transport.connect()
    if not queues:
        queues = [dlqprefix + ".>"]
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
