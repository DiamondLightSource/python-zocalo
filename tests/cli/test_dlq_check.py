from __future__ import annotations

from unittest import mock

import zocalo.cli.dlq_check
from zocalo.configuration import Configuration


@mock.patch("zocalo.cli.dlq_check.JMXAPI")
def test_activemq_dlq_check(mock_jmx):
    cfg = Configuration({})
    _mock = mock.Mock()
    mock_jmx.return_value = _mock
    mock_jmx.return_value.org.apache.activemq.return_value = {
        "status": 200,
        "value": {
            "destinationName=images": {"QueueSize": 2},
            "destinationName=transient": {"QueueSize": 5},
        },
    }
    checked = zocalo.cli.dlq_check.check_dlq(cfg, "zocalo")
    assert checked == {"images": 2, "transient": 5}


def test_activemq_dlq_rabbitmq_check(requests_mock):
    zc = mock.Mock()
    zc.rabbitmqapi = {
        "base_url": "http://fake.com/api",
        "username": "guest",
        "password": "guest",
    }
    requests_mock.get(
        "/api/queues",
        json=[
            {"name": "images", "vhost": "zocalo", "messages": 10, "exclusive": False},
            {
                "name": "dlq.images",
                "vhost": "zocalo",
                "messages": 2,
                "exclusive": False,
            },
            {
                "name": "dlq.transient",
                "vhost": "zocalo",
                "messages": 5,
                "exclusive": False,
            },
        ],
    )
    requests_mock.get("/api/health/checks/alarms", json={"status": "ok"})

    checked = zocalo.cli.dlq_check.check_dlq_rabbitmq(zc, "zocalo")
    assert checked == {"dlq.images": 2, "dlq.transient": 5}
