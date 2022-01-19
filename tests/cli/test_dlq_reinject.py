from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from unittest import mock

import workflows.transport
from workflows.transport.common_transport import CommonTransport

from zocalo.cli.dlq_reinject import run


def gen_header_activemq(i):
    return {
        "content-length": "2489",
        "expires": "0",
        "destination": "/queue/zocalo.garbage.per_image_analysis",
        "subscription": "1",
        "message-id": f"ID:foo.bar.com-{i}",
        "timestamp": "1633102156582",
    }


def gen_header_rabbitmq(i, use_datetime=True):
    tstamp = 1633962302 + 30 * i
    if use_datetime:
        tstamp = datetime.fromtimestamp(tstamp)
    return {
        "x-death": [{"time": tstamp, "queue": "garbage.per_image_analysis"}],
        "message-id": f"ID:foo.bar.com-{i}",
    }


def test_dlq_reinject_activemq(mocker, tmp_path):
    mocked_transport = mocker.MagicMock(CommonTransport)
    mocker.patch.object(workflows.transport, "lookup", return_value=mocked_transport)

    dlq_path = tmp_path / "DLQ"
    dlq_path.mkdir()

    for i in range(10):
        with open(dlq_path / f"msg_{i}", "w") as f:
            dlqmsg = {
                "exported": {
                    "date": time.strftime("%Y-%m-%d"),
                    "time": time.strftime("%H:%M:%S"),
                },
                "header": gen_header_activemq(i),
                "message": {
                    "foo": f"{i}",
                },
            }
            json.dump(dlqmsg, f)

    testargs = ["prog"] + [str(dlq_path / f"msg_{i}") for i in range(10)]
    with mock.patch.object(sys, "argv", testargs):
        run()

    mocked_transport().send.assert_has_calls(
        [
            mock.call(
                "zocalo.garbage.per_image_analysis",
                {"foo": f"{i}"},
                headers=mock.ANY,
                ignore_namespace=True,
            )
            for i in range(10)
        ]
    )


def test_dlq_reinject_rabbitmq(mocker, tmp_path):
    mocked_transport = mocker.MagicMock(CommonTransport)
    mocker.patch.object(workflows.transport, "lookup", return_value=mocked_transport)

    dlq_path = tmp_path / "DLQ"
    dlq_path.mkdir()

    for i in range(10):
        with open(dlq_path / f"msg_{i}", "w") as f:
            dlqmsg = {
                "exported": {
                    "date": time.strftime("%Y-%m-%d"),
                    "time": time.strftime("%H:%M:%S"),
                },
                "header": gen_header_rabbitmq(i, use_datetime=False),
                "message": {
                    "foo": f"{i}",
                },
            }
            json.dump(dlqmsg, f)

    testargs = ["prog", "--transport", "PikaTransport"] + [
        str(dlq_path / f"msg_{i}") for i in range(10)
    ]
    with mock.patch.object(sys, "argv", testargs):
        run()

    mocked_transport().send.assert_has_calls(
        [
            mock.call(
                "garbage.per_image_analysis",
                {"foo": f"{i}"},
                headers=mock.ANY,
            )
            for i in range(10)
        ]
    )
