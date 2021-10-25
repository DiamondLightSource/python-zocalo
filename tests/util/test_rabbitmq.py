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


@pytest.fixture
def rmqapi(zocalo_configuration):
    return rabbitmq.RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)


def test_http_api_request(zocalo_configuration):
    request = rabbitmq.http_api_request(zocalo_configuration, api_path="/queues")
    assert request.get_full_url() == "http://rabbitmq.burrow.com:12345/api/queues"


def test_api_health_checks(requests_mock, rmqapi):
    requests_mock.get(re.compile("/health/checks/"), json={"status": "ok"})
    success, failures = rmqapi.health_checks
    assert not failures
    assert success
    for k, v in success.items():
        assert k.startswith("health/checks/")
        assert v == {"status": "ok"}


def test_api_health_checks_failures(requests_mock, rmqapi):
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
    success, failures = rmqapi.health_checks
    assert failures
    assert success
    assert len(failures) == 1
    for k, v in success.items():
        assert k.startswith("health/checks/")
        assert v == {"status": "ok"}
    for k, v in failures.items():
        assert k.startswith("health/checks/port-listener/")
        assert v == expected_json


def test_api_queues(requests_mock, rmqapi):
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
    assert rmqapi.queues() == [rabbitmq.QueueInfo(**queue)]

    # Now call with vhost=...
    requests_mock.get("/api/queues/zocalo", json=[queue])
    assert rmqapi.queues(vhost="zocalo") == [rabbitmq.QueueInfo(**queue)]

    # Now call with vhost=..., name=...
    requests_mock.get(f"/api/queues/zocalo/{queue['name']}", json=queue)
    assert rmqapi.queues(vhost="zocalo", name=queue["name"]) == rabbitmq.QueueInfo(
        **queue
    )


def test_api_queue_declare(requests_mock, rmqapi):
    qspec = rabbitmq.QueueSpec(
        name="foo", auto_delete=True, arguments={"x-single-active-consumer": True}
    )
    requests_mock.put("/api/queues/zocalo/foo")
    rmqapi.queue_declare(vhost="zocalo", queue=qspec)
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "PUT"
    assert history.url.endswith("/api/queues/zocalo/foo")
    assert history.json() == {"auto_delete": True, "arguments": qspec.arguments}


def test_api_queue_delete(requests_mock, rmqapi):
    requests_mock.delete("/api/queues/zocalo/foo")
    requests_mock.delete("/api/queues/zocalo/bar")
    rmqapi.queue_delete(vhost="zocalo", name="foo")
    rmqapi.queue_delete(vhost="zocalo", name="bar", if_unused=True, if_empty=True)
    assert requests_mock.call_count == 2
    for history in requests_mock.request_history:
        assert history.method == "DELETE"
    assert requests_mock.request_history[0].url.endswith(
        "/api/queues/zocalo/foo?if_unused=False&if_empty=False"
    )
    assert requests_mock.request_history[1].url.endswith(
        "/api/queues/zocalo/bar?if_unused=True&if_empty=True"
    )


def test_api_nodes(requests_mock, rmqapi):
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
    assert rmqapi.nodes() == [rabbitmq.NodeInfo(**node)]

    # Now call with name=...
    requests_mock.get(f"/api/nodes/{node['name']}", json=node)
    assert rmqapi.nodes(name=node["name"]) == rabbitmq.NodeInfo(**node)


@pytest.mark.parametrize("name", ["", "foo"])
def test_api_exchanges(name, requests_mock, rmqapi):
    exchange = {
        "arguments": {},
        "auto_delete": False,
        "durable": True,
        "internal": False,
        "message_stats": {
            "publish_in": 156447,
            "publish_in_details": {"rate": 0.4},
            "publish_out": 156445,
            "publish_out_details": {"rate": 0.4},
        },
        "name": name,
        "type": "direct",
        "user_who_performed_action": "rmq-internal",
        "vhost": "foo",
    }

    # First call rmq.exchanges() with defaults
    requests_mock.get("/api/exchanges", json=[exchange])
    assert rmqapi.exchanges() == [rabbitmq.ExchangeInfo(**exchange)]

    # Now call with vhost=...
    requests_mock.get("/api/exchanges/zocalo/", json=[exchange])
    assert rmqapi.exchanges(vhost="zocalo") == [rabbitmq.ExchangeInfo(**exchange)]

    # Now call with vhost=..., name=...
    requests_mock.get(
        f"/api/exchanges/{exchange['vhost']}/{exchange['name']}/", json=exchange
    )
    assert rmqapi.exchanges(
        vhost=exchange["vhost"], name=exchange["name"]
    ) == rabbitmq.ExchangeInfo(**exchange)


@pytest.mark.parametrize("name", ["", "foo"])
def test_api_exchange_declare(name, requests_mock, rmqapi):
    exchange_spec = rabbitmq.ExchangeSpec(
        name=name,
        type="fanout",
        durable=True,
        auto_delete=True,
        internal=False,
    )
    requests_mock.put(f"/api/exchanges/zocalo/{name}/")
    rmqapi.exchange_declare(vhost="zocalo", exchange=exchange_spec)
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "PUT"
    assert history.url.endswith(f"/api/exchanges/zocalo/{name}/")
    assert history.json() == {
        "type": "fanout",
        "auto_delete": True,
        "durable": True,
        "auto_delete": True,
    }


def test_api_connections(requests_mock, rmqapi):
    connection = {
        "auth_mechanism": "PLAIN",
        "connected_at": 1634716019864,
        "frame_max": 131072,
        "host": "123.24.5.67",
        "name": "123.24.5.67:12345 -> 123.24.5.67:54321",
        "node": "rabbit@cs05r-sc-serv-26",
        "peer_host": "123.24.5.67",
        "peer_port": 12345,
        "port": 54321,
        "protocol": "AMQP 0-9-1",
        "ssl": False,
        "state": "running",
        "timeout": 60,
        "user": "foo",
        "vhost": "bar",
        "channels": 1,
    }

    # First call rmq.connections() with defaults
    requests_mock.get("/api/connections", json=[connection])
    assert rmqapi.connections() == [rabbitmq.ConnectionInfo(**connection)]

    # Now call with name=...
    requests_mock.get(f"/api/connections/{connection['name']}/", json=connection)
    assert rmqapi.connections(name=connection["name"]) == rabbitmq.ConnectionInfo(
        **connection
    )
