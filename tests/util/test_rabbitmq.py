import json
import urllib.request

import pytest

import zocalo.configuration
from zocalo.util.rabbitmq import RabbitMQAPI, http_api_request


@pytest.fixture
def zocalo_configuration(mocker):
    zc = mocker.MagicMock(zocalo.configuration.Configuration)
    zc.rabbitmqapi = {
        "base_url": "http://rabbitmq.burrow.com:12345/api",
        "username": "carrots",
        "password": "carrots",
    }
    return zc


def test_http_api_request(zocalo_configuration):
    request = http_api_request(zocalo_configuration, api_path="/queues")
    assert request.get_full_url() == "http://rabbitmq.burrow.com:12345/api/queues"


def test_api_health_checks(mocker, zocalo_configuration):
    mock_api = mocker.patch("zocalo.util.rabbitmq.http_api_request")
    mock_url = mocker.patch("zocalo.util.rabbitmq.urllib.request.urlopen")
    mock_api.return_value = ""
    mock_url.return_value = mocker.MagicMock()
    mock_url.return_value.__enter__.return_value.read.return_value = json.dumps(
        {"status": "ok"}
    )
    rmq = RabbitMQAPI(zocalo_configuration)
    success, failures = rmq.health_checks
    assert not failures
    assert success
    for k, v in success.items():
        assert k.startswith("/health/checks/")
        assert v == {"status": "ok"}


def test_api_health_checks_failures(mocker, zocalo_configuration):
    mock_api = mocker.patch("zocalo.util.rabbitmq.http_api_request")
    mock_url = mocker.patch("zocalo.util.rabbitmq.urllib.request.urlopen")
    mock_api.return_value = ""
    mock_url.return_value = mocker.MagicMock()
    mock_url.return_value.__enter__.return_value.read.side_effect = (
        urllib.error.HTTPError(
            "http://foo.com", 503, "Service Unavailable", mocker.Mock(), mocker.Mock()
        )
    )
    rmq = RabbitMQAPI(zocalo_configuration)
    success, failures = rmq.health_checks
    assert failures
    assert not success
    for k, v in success.items():
        assert k.startswith("/health/checks/")
        assert v == "HTTP Error 503: Service Unavailable"


def test_api_queues(mocker, zocalo_configuration):
    queues = [
        {
            "consumers": 0,
            "memory": 110112,
            "message_stats": {
                "deliver_get": 33,
                "deliver_get_details": {"rate": 0},
                "publish": 22,
                "publish_details": {"rate": 0},
            },
            "messages": 0,
            "messages_ready": 0,
            "messages_unacknowledged": 0,
            "name": "foo",
            "vhost": "zocalo",
        },
    ]

    mock_api = mocker.patch("zocalo.util.rabbitmq.http_api_request")
    mock_url = mocker.patch("zocalo.util.rabbitmq.urllib.request.urlopen")
    mock_api.return_value = ""
    mock_url.return_value = mocker.MagicMock()
    mock_url.return_value.__enter__.return_value.read.return_value = json.dumps(queues)
    rmq = RabbitMQAPI(zocalo_configuration)
    assert rmq.queues == queues


def test_api_nodes(mocker, zocalo_configuration):
    nodes = {
        "name": "rabbit@pooter123",
        "mem_limit": 80861855744,
        "mem_alarm": False,
        "mem_used": 143544320,
        "disk_free_limit": 50000000,
        "disk_free_alarm": False,
        "disk_free": 875837644800,
        "fd_total": 32768,
        "fd_used": 56,
        "io_file_handle_open_attempt_count": 647,
        "sockets_total": 29401,
        "sockets_used": 0,
        "gc_num": 153378077,
        "gc_bytes_reclaimed": 7998215046336,
        "proc_total": 1048576,
        "proc_used": 590,
        "run_queue": 1,
    }

    mock_api = mocker.patch("zocalo.util.rabbitmq.http_api_request")
    mock_url = mocker.patch("zocalo.util.rabbitmq.urllib.request.urlopen")
    mock_api.return_value = ""
    mock_url.return_value = mocker.MagicMock()
    mock_url.return_value.__enter__.return_value.read.return_value = json.dumps(nodes)
    rmq = RabbitMQAPI(zocalo_configuration)
    assert rmq.queues == nodes
