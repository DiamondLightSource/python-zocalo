from __future__ import annotations

from unittest import mock

import workflows.transport
from workflows.transport.common_transport import CommonTransport

from zocalo.cli.queue_drain import run


def test_queue_drain(mocker, capsys):
    filtered_header = {
        "priority": "4",
        "workflows-recipe": "True",
        "persistent": "true",
    }

    def mock_subscribe(source, receive_message, acknowledgement):
        for i in range(10):
            header = {
                **filtered_header,
                "content-length": "2489",
                "expires": "0",
                "destination": "/queue/zocalo.garbage.per_image_analysis",
                "subscription": "1",
                "message-id": f"ID:foo.bar.com-{i}",
                "timestamp": "1633102156582",
            }
            message = {
                "foo": f"{i}",
            }
            receive_message(header, message)

    mocked_transport = mocker.MagicMock(CommonTransport)
    mocker.patch.object(workflows.transport, "lookup", return_value=mocked_transport)
    mocked_transport().subscribe = mock_subscribe

    run(["source", "destination", "--wait", "0.1", "--stop", "1.5"])

    captured = capsys.readouterr()
    assert "10 message(s) drained, no message seen for" in captured.out

    mocked_transport().send.assert_has_calls(
        [
            mock.call(
                "destination",
                {"foo": f"{i}"},
                headers=filtered_header,
                transaction=mock.ANY,
            )
            for i in range(10)
        ]
    )
