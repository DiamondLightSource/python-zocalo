import argparse
import base64
import configparser
import functools
import hashlib
import logging
import random
import sys
from pathlib import Path
from typing import Dict, List

import yaml

import zocalo.configuration
from zocalo.util.rabbitmq import (
    BindingSpec,
    ExchangeSpec,
    PolicySpec,
    QueueSpec,
    RabbitMQAPI,
    UserInfo,
    UserSpec,
)

logger = logging.getLogger("zocalo.cli.configure_rabbitmq")


class _RabbitMQAPI(RabbitMQAPI):
    @functools.singledispatchmethod  # type: ignore
    def create_component(self, component):
        raise NotImplementedError(f"Component {component} not recognised")

    @functools.singledispatchmethod  # type: ignore
    def delete_component(self, component):
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
            properties_key=binding.properties_key,
        )

    @create_component.register  # type: ignore
    def _(self, exchange: ExchangeSpec):
        self.exchange_declare(exchange)

    @delete_component.register  # type: ignore
    def _(self, exchange: ExchangeSpec, **kwargs):
        self.exchange_delete(vhost=exchange.vhost, name=exchange.name, **kwargs)

    @create_component.register  # type: ignore
    def _(self, policy: PolicySpec):
        self.set_policy(policy)

    @delete_component.register  # type: ignore
    def _(self, policy: PolicySpec):
        self.clear_policy(vhost=policy.vhost, name=policy.name)

    @create_component.register  # type: ignore
    def _(self, queue: QueueSpec):
        self.queue_declare(queue)

    @delete_component.register  # type: ignore
    def _(self, queue: QueueSpec, if_unused: bool = False, if_empty: bool = False):
        self.queue_delete(
            vhost=queue.vhost, name=queue.name, if_unused=if_unused, if_empty=if_empty
        )

    @create_component.register  # type: ignore
    def _(self, user: UserSpec):
        self.add_user(user)

    @delete_component.register  # type: ignore
    def _(self, user: UserSpec):
        self.delete_user(name=user.name)


@functools.singledispatch
def _info_to_spec(incoming, infos: list):
    cls = type(incoming)
    return [cls(**i.dict()) for i in infos]


@_info_to_spec.register  # type: ignore
def _(incoming: UserSpec, infos: list):
    cls = type(incoming)

    def _dict(info: UserInfo) -> dict:
        d = {k: v for k, v in info.dict().items() if k != "tags"}
        d["tags"] = ",".join(info.dict()["tags"])
        return d

    return [cls(**(_dict(i))) for i in infos]


@functools.singledispatch
def _skip(comp) -> bool:
    return False


@_skip.register  # type: ignore
def _(comp: QueueSpec) -> bool:
    if comp.name == "" or "amq." in comp.name:
        return True
    if comp.auto_delete or comp.exclusive:
        return True
    return False


@_skip.register  # type: ignore
def _(comp: BindingSpec) -> bool:
    if comp.source == "" or "amq." in comp.source:
        return True
    return False


def update_config(api: _RabbitMQAPI, incoming, current):
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


def hash_password(passwd: str, seed: int) -> str:
    random.seed(seed)
    intsalt = random.getrandbits(4 * 8)
    salt = intsalt.to_bytes(4, sys.byteorder)
    utf8 = passwd.encode("utf-8")
    temp1 = salt + utf8
    temp2 = hashlib.sha256(temp1).digest()  # lgtm
    salted_hash = salt + temp2
    pass_hash = base64.b64encode(salted_hash)
    return pass_hash.decode()


def get_user_specs(config_files: List[Path], seed: int = 0) -> List[UserSpec]:
    users = []
    for config_file in config_files:
        config = configparser.ConfigParser()
        config.read(config_file)
        users.append(
            UserSpec(
                name=config["rabbitmq"]["username"],
                password_hash=hash_password(config["rabbitmq"]["password"], seed),
                hashing_algorithm="rabbit_password_hashing_sha256",
                tags=config["rabbitmq"].get("tags", ""),
            )
        )
    return users


def get_binding_specs(group: Dict) -> List[BindingSpec]:
    source = group.get("bindings", "")
    vhost = group.get("vhost", "/")
    bspecs = [
        BindingSpec(
            vhost=vhost,
            source=source,
            destination=name,
            destination_type="q",
            routing_key=name,
            arguments={},
            properties_key=name,
        )
        for name in group["names"]
    ]
    return bspecs


def get_queue_specs(group: Dict) -> List[QueueSpec]:
    qtype = group.get("settings", {}).get("queues", {}).get("type", "classic")
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
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": f"dlq.{name}",
                "x-single-active-consumer": single_active_consumer,
            },
            auto_delete=False,
            durable=True,
        )
        for name in group["names"]
    ]

    # Add dead-letter queues within the default exchange with the "dlq." prefix
    qspecs.extend(
        [
            QueueSpec(
                name=f"dlq.{name}",
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


def get_exchange_specs(group: Dict) -> List[ExchangeSpec]:
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


def get_policy_specs(policies: Dict) -> List[PolicySpec]:
    return [
        PolicySpec(
            name=policy["name"],
            pattern=policy.get("pattern", "^amq."),
            definition=policy.get("definition", {}),
            priority=policy.get("priority", 0),
            apply_to=policy.get("apply-to", "queues"),
            vhost=policy.get("vhost", "/"),
        )
        for policy in policies
    ]


def run():
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    zc = zocalo.configuration.from_file()
    zc.activate_environment("live")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config_file", dest="config_file", help="RabbitMQ configuration yaml file"
    )
    parser.add_argument(
        "--seed",
        dest="seed",
        help="Seed used in random salt generation for password hashing",
    )
    api = _RabbitMQAPI.from_zocalo_configuration(zc)
    try:
        rmq_config = zc.storage["zocalo.rabbitmq_user_config"]
    except Exception as e:
        logger.error(
            "Problem with Zocalo configuration file. Possibly zocalo.rabbitmq_user_config storage plugin is missing"
        )
        raise e
    args = parser.parse_args()
    rmq_config_file = args.config_file
    seed = args.seed

    with open(rmq_config_file) as in_file:
        yaml_data = yaml.safe_load(in_file)
    configuration_files = Path(rmq_config).glob("**/*.ini")
    user_specs = get_user_specs(configuration_files, seed=seed)

    queue_specs = []
    exchange_specs = []
    binding_specs = []
    for group in yaml_data["groups"]:
        if group.get("settings", {}).get("broadcast"):
            exchange_specs.extend(get_exchange_specs(group))
        else:
            queue_specs.extend(get_queue_specs(group))
            binding_specs.extend(get_binding_specs(group))

    policies = get_policy_specs(yaml_data["policies"])

    update_config(api, user_specs, api.users())
    update_config(api, policies, api.policies())
    update_config(api, queue_specs, api.queues())
    update_config(api, exchange_specs, api.exchanges())
    permanent_bindings = []
    # don't remove bindings to temporary queues
    queues = api.queues()
    for b in api.bindings():
        q = [qu for qu in queues if qu.vhost == b.vhost and qu.name == b.destination][0]
        if q.auto_delete or q.exclusive:
            continue
        permanent_bindings.append(b)
    update_config(api, binding_specs, permanent_bindings)


if __name__ == "__main__":
    run()