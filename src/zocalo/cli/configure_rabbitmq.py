from __future__ import annotations

import argparse
import configparser
import functools
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
import yaml
from pydantic import BaseModel

import zocalo.configuration
from zocalo.util.rabbitmq import (
    BindingSpec,
    ExchangeSpec,
    PermissionSpec,
    PolicySpec,
    QueueSpec,
    UserSpec,
    VHostSpec,
    hash_password,
)
from zocalo.util.rabbitmq import RabbitMQAPI as _RabbitMQAPI

logger = logging.getLogger("zocalo.cli.configure_rabbitmq")


class RabbitMQAPI(_RabbitMQAPI):
    @functools.singledispatchmethod  # type: ignore
    def create_component(self, component: BaseModel):
        raise NotImplementedError(f"Component {component} not recognised")

    @functools.singledispatchmethod  # type: ignore
    def delete_component(self, component: BaseModel):
        raise NotImplementedError(f"Component {component} not recognised")

    @create_component.register  # type: ignore
    def _(self, binding: BindingSpec):
        self.binding_declare(binding)

    @delete_component.register  # type: ignore
    def _(self, binding: BindingSpec):
        self.bindings_delete(
            vhost=binding.vhost,
            source=binding.source,
            destination=binding.destination,
            destination_type=binding.destination_type.value,
        )

    @create_component.register  # type: ignore
    def _(self, exchange: ExchangeSpec):
        self.exchange_declare(exchange)

    @delete_component.register  # type: ignore
    def _(self, exchange: ExchangeSpec, **kwargs):
        self.exchange_delete(vhost=exchange.vhost, name=exchange.name, **kwargs)

    @create_component.register  # type: ignore
    def _(self, vhost: VHostSpec):
        self.add_vhost(vhost)

    @delete_component.register  # type: ignore
    def _(self, vhost: VHostSpec):
        self.delete_vhost(name=vhost.name)

    @create_component.register  # type: ignore
    def _(self, permissions: PermissionSpec):
        self.set_permissions(permissions)

    @delete_component.register  # type: ignore
    def _(self, permissions: PermissionSpec):
        self.clear_permissions(vhost=permissions.vhost, user=permissions.user)


@functools.singledispatch
def _info_to_spec(incoming, infos: list):
    cls = type(incoming)
    return [cls(**i.dict()) for i in infos]


@functools.singledispatch
def _skip(comp) -> bool:
    return False


@_skip.register  # type: ignore
def _(comp: ExchangeSpec) -> bool:
    if comp.name == "" or "amq." in comp.name:
        return True
    return False


@_skip.register  # type: ignore
def _(comp: BindingSpec) -> bool:
    if comp.source == "" or "amq." in comp.source:
        return True
    return False


def update_config(
    api: RabbitMQAPI, incoming: List[BaseModel], current: List[BaseModel]
):
    cls = type(incoming[0])
    current = _info_to_spec(incoming[0], current)
    for cc in current:
        if cc in incoming:
            if hasattr(cc, "name"):
                logger.debug(f"{cls.__name__} {cc.name} already exists")
            elif hasattr(cc, "source"):
                logger.debug(
                    f"{cls.__name__} {cc.source or 'default'}->{cc.destination} already exists"
                )
        else:
            if _skip(cc):
                continue
            logger.info(f"deleting {cls.__name__} {cc}")
            api.delete_component(cc)
    for ic in incoming:
        if ic not in current:
            logger.info(f"creating {cls.__name__} {ic}")
            api.create_component(ic)


def get_vhost_specs(vhosts: dict) -> List[VHostSpec]:
    vhost_specs = []
    for vhost in vhosts:
        vhost_specs.append(
            VHostSpec(
                name=vhost["name"],
                description=vhost.get("description", ""),
                tags=vhost.get("tags", []),
                tracing=vhost.get("tracing", False),
            )
        )
    return vhost_specs


def get_permission_specs(permissions: dict) -> List[PermissionSpec]:
    permission_specs = []
    for permission in permissions:
        permission_specs.append(PermissionSpec(**permission))
    return permission_specs


def get_binding_specs(bindings: dict) -> List[BindingSpec]:
    binding_specs = []
    for binding in bindings:
        binding_specs.append(
            BindingSpec(
                source=binding["source"],
                destination=binding["destination"],
                destination_type=binding.get("destination_type", "q"),
                routing_key=binding.get("routing_key", binding["destination"]),
                vhost=binding["vhost"],
                arguments=binding.get("arguments", {}),
            )
        )
    return binding_specs


def get_binding_specs_for_group(group: dict) -> List[BindingSpec]:
    sources = group.get("bindings", [""])
    vhost = group.get("vhost", "/")
    return [
        BindingSpec(
            vhost=vhost,
            source=source,
            destination=name,
            destination_type="q",
            routing_key=name,
            arguments={},
            properties_key=name,
        )
        for source in sources
        for name in group["names"]
    ]


def get_queue_specs(group: dict) -> List[QueueSpec]:
    queue_settings = group.get("settings", {}).get("queues", {})
    qtype = queue_settings.get("type", "classic")
    dlq_pattern = queue_settings.get("dead-letter-routing-key-pattern")
    dlq_exchange = queue_settings.get("dead-letter-exchange", "")
    dlq_create = queue_settings.get("dead-letter-queue-create", True)
    vhost = group.get("vhost", "/")
    single_active_consumer = group.get("settings", {}).get(
        "single_active_consumer", False
    )

    qspecs = [
        QueueSpec(
            name=name,
            vhost=vhost,
            arguments={
                "x-queue-type": qtype,
                **(
                    {"x-single-active-consumer": single_active_consumer}
                    if qtype != "stream"
                    else {}
                ),
                **(
                    {
                        "x-dead-letter-exchange": dlq_exchange,
                        "x-dead-letter-routing-key": dlq_pattern.format(name=name),
                    }
                    if dlq_pattern
                    else {}
                ),
            },
            auto_delete=False,
            durable=True,
        )
        for name in group["names"]
    ]

    # Add dead-letter queues within the default exchange with the "dlq." prefix
    if dlq_create and dlq_pattern:
        qspecs.extend(
            [
                QueueSpec(
                    name=dlq_pattern.format(name=name),
                    vhost=vhost,
                    arguments={
                        "x-queue-type": qtype,
                    },
                    auto_delete=False,
                    durable=True,
                )
                for name in group["names"]
            ]
        )
    return qspecs


def get_exchange_specs(exchanges: dict) -> List[ExchangeSpec]:
    return [
        ExchangeSpec(
            **exchange,
        )
        for exchange in exchanges
    ]


def get_exchange_specs_for_group(group: dict) -> List[ExchangeSpec]:
    vhost = group.get("vhost", "/")
    if group.get("settings", {}).get("broadcast"):
        etype = "fanout"
    else:
        etype = group.get("settings", {}).get("exchanges", {}).get("type", "direct")

    return [
        ExchangeSpec(
            arguments={},
            auto_delete=False,
            durable=True,
            name=name,
            type=etype,
            vhost=vhost,
        )
        for name in group["names"]
    ]


def _configure_policies(api, policies: List[Dict[str, Any]]):
    existing_policies = {
        (policy.vhost, policy.name): policy for policy in api.policies()
    }
    known_policies: set[Tuple[str, str]] = set()

    for policy in policies:
        policy_id = (policy["vhost"], policy["name"])
        if policy_id in known_policies:
            raise ValueError(f"Configuration defines duplicate policy {policy_id}")
        known_policies.add(policy_id)

        policy_spec = PolicySpec(
            vhost=policy.get("vhost", "/"),
            name=policy["name"],
            pattern=policy.get("pattern", "^amq."),
            definition=policy.get("definition", {}),
            priority=policy.get("priority", 0),
            apply_to=policy.get("apply-to", "queues"),
        )

        if policy_id in existing_policies:
            if existing_policies[policy_id] == policy_spec:
                continue
            logger.info(f"Updating policy: {policy_spec}")
        else:
            logger.info(f"Creating policy: {policy_spec}")
        api.set_policy(policy_spec)

    for policy_id in set(existing_policies) - known_policies:
        logger.info(f"Removing undefined policy {policy_id}")
        api.clear_policy(vhost=policy_id[0], name=policy_id[1])


def _configure_queues(api, queues: List[QueueSpec]):
    existing_queues = {(q.vhost, q.name): q for q in api.queues()}
    known_queues: set[Tuple[str, str]] = set()

    for queue_spec in queues:
        queue_id = (queue_spec.vhost, queue_spec.name)
        if queue_id in known_queues:
            raise ValueError(f"Configuration defines duplicate queue {queue_id}")
        known_queues.add(queue_id)

        if queue_id in existing_queues:
            equivalent_definition = all(
                getattr(existing_queues[queue_id], key) == value
                for key, value in queue_spec
            )
            if equivalent_definition:
                continue
            logger.info(f"Updating queue: {queue_spec}")
        else:
            logger.info(f"Creating queue: {queue_spec}")
        api.queue_declare(queue_spec)

    for queue_id in set(existing_queues) - known_queues:
        if (
            existing_queues[queue_id].name == ""
            or existing_queues[queue_id].name.startswith("amq.")
            or existing_queues[queue_id].auto_delete
            or existing_queues[queue_id].exclusive
        ):
            # Leave temporary queues alone
            continue
        logger.info(f"Removing undefined queue {queue_id}")
        api.queue_delete(vhost=queue_id[0], name=queue_id[1])


def _configure_users(api, rabbitmq_user_config_area: Path):
    existing_users = {user.name: user for user in api.users()}

    planned_users: Dict[str, Path] = {}
    for config_file in rabbitmq_user_config_area.glob("**/*.ini"):
        try:
            config = configparser.ConfigParser()
            config.read(config_file)
            username = config["rabbitmq"]["username"]
            password = config["rabbitmq"]["password"]
            assert username, "Configuration file does not contain a username"
            assert password, "Configuration file does not specify a password"
            tags = config["rabbitmq"].get("tags", "").split(",")
        except Exception:
            raise ValueError(f"Could not parse configuration file {config_file}")
        if username in planned_users:
            raise ValueError(
                f"Configuration file {config_file} declares user {username}, who was previously declared in {planned_users[username]}"
            )
        planned_users[username] = config_file

        if username in existing_users:
            hashed_password = hash_password(
                password, salt=existing_users[username].password_hash
            )
            if existing_users[username].password_hash == hashed_password and set(
                existing_users[username].tags
            ) == set(tags):
                continue
            logger.info(
                f"Updating user {username} due to password/tag mismatch (tags={tags})"
            )
        else:
            hashed_password = hash_password(password)
            logger.info(
                f"Creating user {username} not defined on the server (tags={tags})"
            )
        api.user_put(
            UserSpec(
                name=username,
                password_hash=hashed_password,
                hashing_algorithm="rabbit_password_hashing_sha256",
                tags=tags,
            )
        )

    for user in set(existing_users) - set(planned_users):
        logger.info(f"Removing user {user} not defined in the configuration")
        api.user_delete(name=user)


def run():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    zc = zocalo.configuration.from_file()
    zc.activate()
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("configuration", help="RabbitMQ configuration yaml file")
    parser.add_argument(
        "--user-config",
        action="store",
        dest="user_config",
        type=Path,
        help="Path to directory containing *.ini files containing RabbitMQ\n"
        "    user credentials in the form:\n"
        "    [rabbitmq]\n"
        "    username = user\n"
        "    password = letmein\n"
        "    tags = comma,separated,tags",
    )
    zc.add_command_line_options(parser)
    args = parser.parse_args()

    api = RabbitMQAPI.from_zocalo_configuration(zc)

    with open(args.configuration) as in_file:
        yaml_data = yaml.safe_load(in_file)

    try:
        if args.user_config:
            _configure_users(api, args.user_config)

        # configure vhosts
        if vhost_specs := get_vhost_specs(yaml_data.get("vhosts", [])):
            current_vhosts_excluding_default = [
                vhost for vhost in api.vhosts() if vhost.name != "/"
            ]
            update_config(api, vhost_specs, current_vhosts_excluding_default)

        # configure permissions
        if permission_specs := get_permission_specs(yaml_data.get("permissions", [])):
            update_config(api, permission_specs, api.permissions())

        # configure policies
        _configure_policies(api, yaml_data["policies"])

        queue_specs = []
        exchange_specs = get_exchange_specs(yaml_data["exchanges"])
        binding_specs = get_binding_specs(yaml_data.get("bindings", []))
        for group in yaml_data["groups"]:
            if group.get("settings", {}).get("broadcast"):
                exchange_specs.extend(get_exchange_specs_for_group(group))
            else:
                queue_specs.extend(get_queue_specs(group))
                binding_specs.extend(get_binding_specs_for_group(group))

        _configure_queues(api, queue_specs)
        update_config(api, exchange_specs, api.exchanges())
        permanent_bindings = []
        # don't remove bindings to temporary queues
        queues = api.queues()
        for b in api.bindings():
            try:
                q = [
                    qu
                    for qu in queues
                    if qu.vhost == b.vhost and qu.name == b.destination
                ][0]
            except IndexError:
                logger.warning(f"No matching queue found binding {b}")
            else:
                if q.auto_delete or q.exclusive:
                    continue
                permanent_bindings.append(b)
        update_config(api, binding_specs, permanent_bindings)
    except requests.exceptions.HTTPError as e:
        # Specially handle the VHost error, as we used to not setup vhosts
        try:
            if e.response.json()["reason"] == "vhost_not_found":
                logger.error(f"Error 404: VHost not found for url: {e.response.url}")
                sys.exit(1)
        except Exception:
            raise
        logger.error(e)
        sys.exit(1)


if __name__ == "__main__":
    run()
