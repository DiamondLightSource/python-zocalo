from __future__ import annotations

import itertools
from unittest import mock

import workflows.transport
from workflows.transport.common_transport import CommonTransport
from workflows.util import generate_unique_host_id

from zocalo.cli.shutdown import run


def test_shutdown_host(mocker):
    mocked_transport = mocker.MagicMock(CommonTransport)
    mocked_lookup = mocker.patch.object(
        workflows.transport, "lookup", return_value=mocked_transport
    )
    host_prefix = ".".join(generate_unique_host_id().split(".")[:-2])
    hosts = ["uk.ac.diamond.ws123.4567", "ws987.6543"]
    expected_hosts = ["uk.ac.diamond.ws123.4567", f"{host_prefix}.ws987.6543"]
    run(hosts)
    mocked_lookup.assert_called_with("StompTransport")
    mocked_transport().broadcast.assert_has_calls(
        [
            mock.call("command", {"command": "shutdown", "host": host})
            for host in expected_hosts
        ]
    )


def test_shutdown_services(mocker):
    mocked_transport = mocker.MagicMock(CommonTransport)
    mocked_lookup = mocker.patch.object(
        workflows.transport, "lookup", return_value=mocked_transport
    )
    services = ["Foo", "Bar"]
    run(
        list(itertools.chain.from_iterable([["-s", service] for service in services]))
        + ["-t", "PikaTransport"]
    )
    mocked_lookup.assert_called_with("PikaTransport")
    mocked_transport().broadcast.assert_has_calls(
        [
            mock.call("command", {"command": "shutdown", "service": service})
            for service in services
        ]
    )
