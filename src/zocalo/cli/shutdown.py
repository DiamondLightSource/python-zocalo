#
# zocalo.shutdown
#   Stop a zocalo service
#

from __future__ import annotations

import argparse
import socket
import sys

import workflows
import workflows.services
import workflows.transport

import zocalo.configuration


def run(args=None):
    parser = argparse.ArgumentParser()

    # Load configuration
    zc = zocalo.configuration.from_file()
    zc.activate()

    known_services = sorted(workflows.services.get_known_services())
    parser.add_argument("-?", action="help", help=argparse.SUPPRESS)
    parser.add_argument(
        "HOSTS",
        nargs="*",
        type=str,
        help="Specific service instances specified as hostname.pid",
    )
    parser.add_argument(
        "-s",
        "--service",
        dest="services",
        metavar="SVC",
        action="append",
        default=[],
        help="Stop all instances of a service. Use 'none' for instances without "
        "loaded service. Known services: " + ", ".join(known_services),
    )
    zc.add_command_line_options(parser)
    workflows.transport.add_command_line_options(parser, transport_argument=True)
    args = parser.parse_args(args)

    if not args.services and not len(args.HOSTS):
        print("Need to specify one or more services to shut down.")
        print("Either specify service groups with -s or specify specific instances")
        print("as: hostname.pid")
        sys.exit(1)

    transport = workflows.transport.lookup(args.transport)()
    transport.connect()

    for host in args.HOSTS:
        if host.count(".") == 1:
            # See also workflows.util.generate_unique_host_id()
            host = ".".join(reversed(socket.gethostname().split(".")[1:])) + "." + host

        message = {"command": "shutdown", "host": host}
        transport.broadcast("command", message)
        print("Shutting down", host)

    for service in args.services:
        if service.lower() == "none":
            # Special case for placeholder instances
            service = None
        message = {"command": "shutdown", "service": service}
        transport.broadcast("command", message)
        print("Stopping all instances of", service)

    transport.disconnect()
