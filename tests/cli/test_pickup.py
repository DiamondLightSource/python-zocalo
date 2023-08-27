from __future__ import annotations

import json
import sys
import time
import uuid
from unittest import mock

import pytest
import workflows.transport
import zocalo.configuration
from workflows.transport.common_transport import CommonTransport
from zocalo.cli import pickup


@pytest.fixture
def mock_zocalo_configuration(tmp_path):
    mock_zc = mock.MagicMock(zocalo.configuration.Configuration)
    mock_zc.storage = {
        "zocalo.go.fallback_location": str(tmp_path),
    }
    return mock_zc


def test_pickup_empty_filelist_raises_system_exit(mocker, mock_zocalo_configuration):
    mocker.patch.object(
        zocalo.configuration, "from_file", return_value=mock_zocalo_configuration
    )
    with mock.patch.object(sys, "argv", ["prog"]), pytest.raises(SystemExit) as e:
        pickup.run()
        assert e.code == 0


def test_pickup_sends_to_processing_recipe(mocker, mock_zocalo_configuration, tmp_path):
    mocked_transport = mocker.MagicMock(CommonTransport)
    mocker.patch.object(workflows.transport, "lookup", return_value=mocked_transport)
    mocker.patch.object(
        zocalo.configuration, "from_file", return_value=mock_zocalo_configuration
    )
    for i in range(10):
        msg = {
            "headers": {"zocalo.go.user": "foobar", "zocalo.go.host": "example.com"},
            "message": {
                "recipes": [f"thing{i}"],
                "parameters": {"foo": i},
            },
        }
        (tmp_path / str(uuid.uuid4())).write_text(json.dumps(msg))
        time.sleep(0.1)
    with mock.patch.object(sys, "argv", ["prog", "--wait", "0", "--delay", "0"]):
        pickup.run()
    mocked_transport().send.assert_has_calls(
        [
            mock.call(
                "processing_recipe",
                {
                    "recipes": [f"thing{i}"],
                    "parameters": {"foo": i},
                },
                headers=mock.ANY,
            )
            for i in range(10)
        ]
    )
