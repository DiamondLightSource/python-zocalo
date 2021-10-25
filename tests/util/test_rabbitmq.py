import re

import pytest

import zocalo.configuration
import zocalo.util.rabbitmq
from zocalo.util.rabbitmq import NodeInfo, QueueInfo, RabbitMQAPI, http_api_request


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


def test_api_health_checks(requests_mock, zocalo_configuration):
    requests_mock.get(re.compile("/health/checks/"), json={"status": "ok"})
    rmq = RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    success, failures = rmq.health_checks
    assert not failures
    assert success
    for k, v in success.items():
        assert k.startswith("health/checks/")
        assert v == {"status": "ok"}


def test_api_health_checks_failures(requests_mock, zocalo_configuration):
    expected_json = {
        "status": "failed",
        "reason": "No active listener",
        "missing": 1234,
        "ports": [25672, 15672, 1883, 15692, 61613, 5672],
    }
    requests_mock.get(re.compile("/health/checks/"), json={"status": "ok"})
    requests_mock.get(
        re.compile("/health/checks/port-listener"),
        status_code=503,
        reason="No active listener",
        json=expected_json,
    )
    rmq = RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    success, failures = rmq.health_checks
    assert failures
    assert success
    assert len(failures) == 1
    for k, v in success.items():
        assert k.startswith("health/checks/")
        assert v == {"status": "ok"}
    for k, v in failures.items():
        assert k.startswith("health/checks/port-listener/")
        assert v == expected_json


def test_api_queues(requests_mock, zocalo_configuration):
    queue = {
        "consumers": 0,
        "exclusive": False,
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
    }

    # First call rmq.queues() with defaults
    requests_mock.get("/api/queues", json=[queue])
    rmq = RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    assert rmq.queues() == [QueueInfo(**queue)]

    # Now call with vhost=...
    requests_mock.get("/api/queues/zocalo", json=[queue])
    rmq = RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    assert rmq.queues(vhost="zocalo") == [QueueInfo(**queue)]

    # Now call with vhost=..., name=...
    requests_mock.get(f"/api/queues/zocalo/{queue['name']}", json=queue)
    rmq = RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    assert rmq.queues(vhost="zocalo", name=queue["name"]) == QueueInfo(**queue)


def test_api_nodes(requests_mock, zocalo_configuration):
    node = {
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
        "running": True,
        "type": "disc",
    }

    # First call rmq.nodes() with defaults
    requests_mock.get("/api/nodes", json=[node])
    rmq = RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    assert rmq.nodes() == [NodeInfo(**node)]

    # Now call with name=...
    requests_mock.get(f"/api/nodes/{node['name']}", json=node)
    rmq = RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    assert rmq.nodes(name=node["name"]) == NodeInfo(**node)
