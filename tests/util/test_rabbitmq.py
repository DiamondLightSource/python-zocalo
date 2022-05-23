from __future__ import annotations

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
def rmqapi(requests_mock, zocalo_configuration):
    requests_mock.get(re.compile("/health/checks/alarms"), json={"status": "ok"})
    api = rabbitmq.RabbitMQAPI.from_zocalo_configuration(zocalo_configuration)
    requests_mock.reset_mock()
    return api


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


@pytest.fixture
def queue_spec():
    return rabbitmq.QueueSpec(
        name="foo",
        auto_delete=True,
        vhost="zocalo",
        arguments={"x-single-active-consumer": True},
    )


def test_api_queue_declare(requests_mock, rmqapi, queue_spec):
    requests_mock.put("/api/queues/zocalo/foo")
    rmqapi.queue_declare(queue=queue_spec)
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "PUT"
    assert history.url.endswith("/api/queues/zocalo/foo")
    assert history.json() == {
        "auto_delete": True,
        "arguments": queue_spec.arguments,
    }


def test_api_queue_delete(requests_mock, rmqapi, queue_spec):
    requests_mock.delete("/api/queues/zocalo/foo")
    rmqapi.queue_delete(vhost="zocalo", name="foo", if_unused=True, if_empty=True)
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "DELETE"
    assert history.url.endswith("/api/queues/zocalo/foo?if-unused=True&if-empty=True")


def test_api_bindings(requests_mock, rmqapi):
    binding = {
        "source": "foo",
        "destination": "bar",
        "destination_type": "q",
        "arguments": {},
        "routing_key": "bar",
        "properties_key": "bar",
        "vhost": "zocalo",
    }
    response = {
        "source": "foo",
        "destination": "bar",
        "destination_type": "queue",
        "arguments": {},
        "routing_key": "bar",
        "properties_key": "bar",
        "vhost": "zocalo",
    }

    requests_mock.get("/api/bindings", json=[response])
    assert rmqapi.bindings() == [rabbitmq.BindingInfo(**binding)]

    requests_mock.get("/api/bindings/zocalo", json=[response])
    assert rmqapi.bindings(vhost="zocalo") == [rabbitmq.BindingInfo(**binding)]

    requests_mock.get(
        f"/api/bindings/zocalo/e/{binding['source']}/q/{binding['destination']}",
        json=[response],
    )
    assert rmqapi.bindings(
        vhost="zocalo",
        source=binding["source"],
        destination=binding["destination"],
        destination_type="q",
    ) == [rabbitmq.BindingInfo(**binding)]


@pytest.fixture
def binding_spec():
    return rabbitmq.BindingSpec(
        source="foo",
        destination="bar",
        destination_type="q",
        arguments={},
        routing_key="bar",
        vhost="zocalo",
    )


def test_api_binding_declare(requests_mock, rmqapi, binding_spec):
    requests_mock.post("/api/bindings/zocalo/e/foo/q/bar")
    rmqapi.binding_declare(binding=binding_spec)
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "POST"
    assert history.url.endswith("/api/bindings/zocalo/e/foo/q/bar")
    assert history.json() == {
        "arguments": binding_spec.arguments,
        "routing_key": "bar",
    }


def test_api_bindings_delete(requests_mock, rmqapi, binding_spec):
    binding = {
        "source": "foo",
        "destination": "bar",
        "destination_type": "queue",
        "arguments": {},
        "routing_key": "bar",
        "properties_key": "bar",
        "vhost": "zocalo",
    }
    requests_mock.get("/api/bindings/zocalo/e/foo/q/bar", json=[binding])
    requests_mock.delete("/api/bindings/zocalo/e/foo/q/bar/bar")
    rmqapi.bindings_delete(
        vhost="zocalo",
        source="foo",
        destination="bar",
        destination_type="q",
    )
    assert requests_mock.call_count == 2
    history = requests_mock.request_history[0]
    assert history.method == "GET"
    assert history.url.endswith("/api/bindings/zocalo/e/foo/q/bar")
    history = requests_mock.request_history[1]
    assert history.method == "DELETE"
    assert history.url.endswith("/api/bindings/zocalo/e/foo/q/bar/bar")


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


def exchange_spec(name):
    return rabbitmq.ExchangeSpec(
        name=name,
        type="fanout",
        durable=True,
        auto_delete=True,
        internal=False,
        vhost="zocalo",
    )


@pytest.mark.parametrize("name", ["", "foo"])
def test_api_exchange_declare(name, requests_mock, rmqapi):
    requests_mock.put(f"/api/exchanges/zocalo/{name}/")
    rmqapi.exchange_declare(exchange=exchange_spec(name))
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "PUT"
    assert history.url.endswith(f"/api/exchanges/zocalo/{name}/")
    assert history.json() == {
        "type": "fanout",
        "auto_delete": True,
        "durable": True,
        "arguments": {},
    }


def test_api_exchange_delete(requests_mock, rmqapi):
    requests_mock.delete("/api/exchanges/zocalo/foo")
    rmqapi.exchange_delete(vhost="zocalo", name="foo", if_unused=True)
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "DELETE"
    assert history.url.endswith("/api/exchanges/zocalo/foo?if-unused=True")


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


def test_api_users(requests_mock, rmqapi):
    user = {
        "name": "guest",
        "password_hash": "guest",
        "hashing_algorithm": "rabbit_password_hashing_sha256",
        "tags": ["administrator"],
    }

    # First call rmq.users() with defaults
    requests_mock.get("/api/users", json=[user])
    assert rmqapi.users() == [rabbitmq.UserSpec(**user)]

    # Now call with name=...
    requests_mock.get(f"/api/users/{user['name']}/", json=user)
    assert rmqapi.user(user["name"]) == rabbitmq.UserSpec(**user)


@pytest.fixture
def user_spec():
    return rabbitmq.UserSpec(
        name="guest",
        password_hash="guest",
        hashing_algorithm="rabbit_password_hashing_sha256",
        tags=["administrator"],
    )


def test_api_add_user(requests_mock, rmqapi, user_spec):
    requests_mock.put(f"/api/users/{user_spec.name}/")
    rmqapi.user_put(user=user_spec)
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "PUT"
    assert history.url.endswith(f"/api/users/{user_spec.name}/")
    assert history.json() == {
        "password_hash": "guest",
        "hashing_algorithm": "rabbit_password_hashing_sha256",
        "tags": "administrator",
    }


def test_api_delete_user(requests_mock, rmqapi, user_spec):
    requests_mock.delete("/api/users/guest/")
    rmqapi.user_delete(name="guest")
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "DELETE"
    assert history.url.endswith("/api/users/guest/")


def test_api_policies(requests_mock, rmqapi):
    policy = {
        "vhost": "foo",
        "name": "redelivery",
        "pattern": "^amq.",
        "apply-to": "queues",
        "definition": {"delivery-limit": 5},
        "priority": 0,
    }

    # First call rmq.policies() with defaults
    requests_mock.get("/api/policies", json=[policy])
    assert rmqapi.policies() == [rabbitmq.PolicySpec(**policy)]

    # Now call with vhost=...
    requests_mock.get(f"/api/policies/{policy['vhost']}/", json=[policy])
    assert rmqapi.policies(vhost=policy["vhost"]) == [rabbitmq.PolicySpec(**policy)]

    # Now call with vhost=..., name=...
    requests_mock.get(f"/api/policies/{policy['vhost']}/{policy['name']}/", json=policy)
    assert rmqapi.policy(
        vhost=policy["vhost"], name=policy["name"]
    ) == rabbitmq.PolicySpec(**policy)


@pytest.fixture
def policy_spec():
    return rabbitmq.PolicySpec(
        name="bar",
        pattern="^amq.",
        apply_to=rabbitmq.PolicyApplyTo.queues,
        definition={"delivery-limit": 5},
        vhost="foo",
    )


def test_api_set_policy(requests_mock, rmqapi, policy_spec):
    requests_mock.put(f"/api/policies/foo/{policy_spec.name}/")
    rmqapi.set_policy(policy=policy_spec)
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "PUT"
    assert history.url.endswith(f"/api/policies/foo/{policy_spec.name}/")
    assert history.json() == {
        "pattern": "^amq.",
        "apply-to": "queues",
        "definition": {"delivery-limit": 5},
    }


def test_api_clear_policy(requests_mock, rmqapi, policy_spec):
    requests_mock.delete("/api/policies/foo/bar/")
    rmqapi.clear_policy(vhost="foo", name="bar")
    assert requests_mock.call_count == 1
    history = requests_mock.request_history[0]
    assert history.method == "DELETE"
    assert history.url.endswith("/api/policies/foo/bar/")
