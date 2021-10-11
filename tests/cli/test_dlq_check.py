import json
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


@mock.patch("zocalo.cli.dlq_check.urllib.request.urlopen")
@mock.patch("zocalo.cli.dlq_check.http_api_request")
def test_activemq_dlq_rabbitmq_check(mock_api, mock_url):
    cfg = Configuration({})
    _mock = mock.MagicMock()
    mock_api.return_value = ""
    mock_url.return_value = _mock
    mock_url.return_value.__enter__.return_value.read.return_value = json.dumps(
        [
            {"name": "images", "vhost": "zocalo", "messages": 10},
            {"name": "dlq.images", "vhost": "zocalo", "messages": 2},
            {"name": "dlq.transient", "vhost": "zocalo", "messages": 5},
        ]
    )

    checked = zocalo.cli.dlq_check.check_dlq_rabbitmq(cfg, "zocalo")
    assert checked == {"dlq.images": 2, "dlq.transient": 5}
