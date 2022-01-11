#
# zocalo.queue_drain
#   Drain one queue into another in a controlled manner
#


from __future__ import annotations

import argparse
import queue
import sys
import time
from datetime import datetime

import workflows.recipe.wrapper
import workflows.transport

import zocalo.configuration


def show_cluster_info(step):
    try:
        print("Beamline " + step["parameters"]["cluster_project"].upper())
    except Exception:
        pass
    try:
        print("Working directory " + step["parameters"]["workingdir"])
    except Exception:
        pass


show_additional_info = {"cluster.submission": show_cluster_info}


def run(args=None):
    # Load configuration
    zc = zocalo.configuration.from_file()
    zc.activate()

    parser = argparse.ArgumentParser(
        usage="zocalo.queue_drain [options] source destination"
    )
    parser.add_argument("-?", action="help", help=argparse.SUPPRESS)
    parser.add_argument("SOURCE", type=str, help="Source queue name")
    parser.add_argument(
        "DEST",
        type=str,
        help="Destination queue name;"
        " use '.' to automatically determine destination for recipe messages",
    )
    parser.add_argument(
        "--wait",
        action="store",
        dest="wait",
        type=float,
        default=5,
        help="Wait this many seconds between deliveries",
    )
    parser.add_argument(
        "--stop",
        action="store",
        dest="stop",
        type=float,
        default=60,
        help="Stop if no message seen for this many seconds (0 = forever)",
    )
    zc.add_command_line_options(parser)
    workflows.transport.add_command_line_options(parser, transport_argument=True)
    args = parser.parse_args(args)

    transport = workflows.transport.lookup(args.transport)()
    transport.connect()

    messages = queue.Queue()

    def receive_message(header, message):
        messages.put((header, message))

    print(f"Reading messages from {args.SOURCE}")
    subscription_id = transport.subscribe(
        args.SOURCE, receive_message, acknowledgement=True
    )

    if args.DEST == ".":
        print("Writing messages to automatically determined destinations")
    else:
        print(f"Writing messages to {args.DEST}")

    message_count = 0
    header_filter = frozenset(
        {
            "content-length",
            "destination",
            "expires",
            "message-id",
            "original-destination",
            "originalExpiration",
            "subscription",
            "timestamp",
            "redelivered",
        }
    )
    drain_start = time.time()
    idle_time = 0
    try:
        while True:
            try:
                header, message = messages.get(True, 0.1)
            except queue.Empty:
                idle_time = idle_time + 0.1
                if args.stop and idle_time > args.stop:
                    break
                continue
            idle_time = 0
            print()
            try:
                print(
                    "Message date: {:%Y-%m-%d %H:%M:%S}".format(
                        datetime.fromtimestamp(int(header["timestamp"]) / 1000)
                    )
                )
            except Exception:
                pass
            target_queue = args.DEST

            try:
                print(f"Recipe ID:    {message['environment']['ID']}")
                r = workflows.recipe.wrapper.RecipeWrapper(message=message)
                if target_queue == ".":
                    target_queue = r.recipe_step["queue"]
                    print(f"Target Queue: {target_queue}")
                additional_info_function = show_additional_info.get(target_queue)
                if additional_info_function:
                    additional_info_function(r.recipe_step)
            except Exception:
                pass

            if target_queue == ".":
                exit("Could not determine target queue for message")

            new_headers = {
                key: header[key] for key in header if key not in header_filter
            }
            txn = transport.transaction_begin(subscription_id=subscription_id)
            transport.send(target_queue, message, headers=new_headers, transaction=txn)
            transport.ack(header, transaction=txn)
            transport.transaction_commit(txn)
            message_count = message_count + 1
            print(
                "%4d message(s) drained in %.1f seconds"
                % (message_count, time.time() - drain_start)
            )
            time.sleep(args.wait)
    except KeyboardInterrupt:
        sys.exit(
            "\nCancelling, %d message(s) drained, %d message(s) unprocessed in memory"
            % (message_count, messages.qsize())
        )
    print(
        "%d message(s) drained, no message seen for %.1f seconds"
        % (message_count, idle_time)
    )
    transport.disconnect()
