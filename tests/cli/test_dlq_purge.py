import os
import sys
from datetime import datetime
from unittest import mock

import workflows.transport
from workflows.transport.common_transport import CommonTransport

from zocalo.cli.dlq_purge import run


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
        "headers": {"x-death": [{"time": tstamp}]},
        "message-id": f"ID:foo.bar.com-{i}",
    }


def test_dlq_purge_activemq(mocker, tmp_path):
    os.chdir(tmp_path)

    def mock_subscribe(source, receive_message, acknowledgement):
        for i in range(10):
            header = gen_header_activemq(i)
            message = {
                "foo": f"{i}",
            }
            receive_message(header, message)

    mocked_transport = mocker.MagicMock(CommonTransport)
    mocker.patch.object(workflows.transport, "lookup", return_value=mocked_transport)
    mocked_transport().subscribe = mock_subscribe

    sys.argv.append("garbage.per_image_analysis")
    run()

    mocked_transport().ack.assert_has_calls(
        [mock.call(gen_header_activemq(i)) for i in range(10)]
    )

    dlq_dirs = list(tmp_path.glob("DLQ/*"))
    assert len(dlq_dirs) == 1
    assert len(list(dlq_dirs[0].glob("**/*"))) == 10


def test_dlq_purge_rabbitmq(mocker, tmp_path):
    os.chdir(tmp_path)

    def mock_subscribe(source, receive_message, acknowledgement):
        for i in range(10):
            header = gen_header_rabbitmq(i)
            message = {
                "foo": f"{i}",
            }
            receive_message(header, message)

    mocked_transport = mocker.MagicMock(CommonTransport)
    mocker.patch.object(workflows.transport, "lookup", return_value=mocked_transport)
    mocked_transport().subscribe = mock_subscribe

    sys.argv.extend(["--transport", "PikaTransport"])
    run()

    mocked_transport().ack.assert_has_calls(
        [
            mock.call(
                gen_header_rabbitmq(i, use_datetime=False),
                subscription_id=f"ID:foo.bar.com-{i}",
            )
            for i in range(10)
        ]
    )

    dlq_dirs = list(tmp_path.glob("DLQ/*"))
    assert len(dlq_dirs) == 1
    assert len(list(dlq_dirs[0].glob("**/*"))) == 10
