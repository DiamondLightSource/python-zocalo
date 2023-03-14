from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

import workflows.transport

import zocalo.configuration


def run():
    zc = zocalo.configuration.from_file()
    zc.activate()
    dropdir = pathlib.Path(zc.storage["zocalo.go.fallback_location"])

    parser = argparse.ArgumentParser(
        usage="zocalo.pickup [options]", description="Processes zocalo.go backlog"
    )

    parser.add_argument("-?", action="help", help=argparse.SUPPRESS)
    parser.add_argument(
        "-d",
        "--delay",
        dest="delay",
        action="store",
        type=int,
        default=2,
        help="Number of seconds to wait between message dispatches",
    )
    parser.add_argument(
        "-w",
        "--wait",
        dest="wait",
        action="store",
        type=int,
        default=60,
        help="Number of seconds to wait initially",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbose",
        action="store_true",
        default=False,
        help="Show raw message before sending",
    )
    zc.add_command_line_options(parser)
    workflows.transport.add_command_line_options(parser, transport_argument=True)
    args = parser.parse_args()

    try:
        files = list(dropdir.iterdir())
    except OSError:
        sys.exit("This program is only available to privileged users")

    print(f"Found {len(files)} files")
    if not files:
        sys.exit()

    if args.wait:
        print(f"Waiting {args.wait} seconds")
        time.sleep(args.wait)

    print(f"Connecting to {args.transport}...")
    transport = workflows.transport.lookup(args.transport)()
    transport.connect()

    file_info = {f: {} for f in files}

    for f, finfo in file_info.items():
        with f.open() as fh:
            data = json.load(fh)
            finfo["message"] = data["message"]
            finfo["headers"] = data["headers"]
        finfo["originating-host"] = finfo["headers"].get("zocalo.go.host")
        finfo["recipes"] = ",".join(finfo["message"].get("recipes", []))
        finfo["mtime"] = f.stat().st_mtime

    count = 0
    file_count = len(file_info)
    for f, finfo in dict(
        sorted(file_info.items(), key=lambda item: item[1]["mtime"])
    ).items():
        print(
            f"Sending {f} from host {file_info[f]['originating-host']}"
            f" with recipes {file_info[f]['recipes']}"
        )
        assert f.exists()
        transport.send(
            "processing_recipe",
            file_info[f]["message"],
            headers=file_info[f]["headers"],
        )
        f.unlink()
        count = count + 1
        print(f"Done ({count} of {file_count})")
        try:
            time.sleep(args.delay)
        except KeyboardInterrupt:
            print("CTRL+C - stopping")
            time.sleep(0.5)
            sys.exit(1)

    transport.disconnect()
