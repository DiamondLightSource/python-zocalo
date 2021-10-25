import re

import pytest

import zocalo.configuration
import zocalo.util.rabbitmq as rabbitmq


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
    request = rabbitmq.http_api_request(zocalo_configuration, api_path="/queues")
    assert request.get_full_url() == "http://rabbitmq.burrow.com:12345/api/queues"


def test_api_health_checks(requests_mock, zocalo_configuration):
    rmq = rabbitmq.RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    requests_mock.get(re.compile("/health/checks/"), json={"status": "ok"})
    success, failures = rmq.health_checks
    assert not failures
    assert success
    for k, v in success.items():
        assert k.startswith("health/checks/")
        assert v == {"status": "ok"}


def test_api_health_checks_failures(requests_mock, zocalo_configuration):
    rmq = rabbitmq.RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
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
    rmq = rabbitmq.RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)

    # First call rmq.queues() with defaults
    requests_mock.get("/api/queues", json=[queue])
    assert rmq.queues() == [rabbitmq.QueueInfo(**queue)]

    # Now call with vhost=...
    requests_mock.get("/api/queues/zocalo", json=[queue])
    assert rmq.queues(vhost="zocalo") == [rabbitmq.QueueInfo(**queue)]

    # Now call with vhost=..., name=...
    requests_mock.get(f"/api/queues/zocalo/{queue['name']}", json=queue)
    assert rmq.queues(vhost="zocalo", name=queue["name"]) == rabbitmq.QueueInfo(**queue)


def test_api_queue_declare(requests_mock, zocalo_configuration):
    rmq = rabbitmq.RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    qspec = rabbitmq.QueueSpec(
        name="foo", auto_delete=True, arguments={"x-single-active-consumer": True}
    )
    requests_mock.put("/api/queues/zocalo/foo")
    rmq.queue_declare(vhost="zocalo", queue=qspec)
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "PUT"
    assert history.url.endswith("/api/queues/zocalo/foo")
    assert history.json() == {"auto_delete": True, "arguments": qspec.arguments}


def test_api_queue_delete(requests_mock, zocalo_configuration):
    rmq = rabbitmq.RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    requests_mock.delete("/api/queues/zocalo/foo")
    requests_mock.delete("/api/queues/zocalo/bar")
    rmq.queue_delete(vhost="zocalo", name="foo")
    rmq.queue_delete(vhost="zocalo", name="bar", if_unused=True, if_empty=True)
    assert requests_mock.call_count == 2
    for history in requests_mock.request_history:
        assert history.method == "DELETE"
    assert requests_mock.request_history[0].url.endswith(
        "/api/queues/zocalo/foo?if_unused=False&if_empty=False"
    )
    assert requests_mock.request_history[1].url.endswith(
        "/api/queues/zocalo/bar?if_unused=True&if_empty=True"
    )


def test_api_nodes(requests_mock, zocalo_configuration):
    rmq = rabbitmq.RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
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
    assert rmq.nodes() == [rabbitmq.NodeInfo(**node)]

    # Now call with name=...
    requests_mock.get(f"/api/nodes/{node['name']}", json=node)
    assert rmq.nodes(name=node["name"]) == rabbitmq.NodeInfo(**node)
