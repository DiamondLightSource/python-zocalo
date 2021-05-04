import logging
import os

import yaml
from marshmallow import INCLUDE, Schema, fields
from workflows.transport.stomp_transport import StompTransport

# To instantiate !include
import zocalo.configuration.utils  # noqa: F401
from zocalo.configuration.plugins import get_known_plugins

logger = logging.getLogger("zocalo.configuration")


class Configuration(dict):
    _implicit_keys = ["version", "environments"]
    _plugins = {}

    def __init__(self, yml_dict):
        if not yml_dict.get("environments"):
            raise KeyError("No environments defined in config")

        plugins = get_known_plugins()
        for key, cfg in yml_dict.items():
            if key in self._implicit_keys:
                continue

            if isinstance(cfg, dict):
                if "plugin" in cfg:
                    if cfg["plugin"] in plugins:
                        if cfg["plugin"] not in self._plugins:
                            self._plugins[cfg["plugin"]] = {}
                        self._plugins[cfg["plugin"]][key] = plugins[
                            cfg["plugin"]
                        ].default(cfg)

                    else:
                        logger.warning(
                            f"Unknown plugin being loaded for {key}: {cfg['plugin']}"
                        )

        super().__init__(yml_dict)

    def get_plugin(self, plugin, env="test"):
        if plugin not in self._plugins:
            raise KeyError(f"Unconfigured plugin requested: {plugin}")

        if env is not None:
            if env in self["environments"]:
                env_tag = self["environments"][env][plugin]
                return self._plugins[plugin][env_tag]
            else:
                raise KeyError(
                    f"Requesting unknown tag {env} from config for plugin {plugin}"
                )

        else:
            logger.debug(
                f"No env specificed for plugin {plugin}, will return first plugin instance"
            )
            return list(self._plugins[plugin].values())[0]

    def has_plugin(self, plugin):
        return plugin in self._plugins


class ConfigSchema(Schema):
    version = fields.Int(required=True)
    environments = fields.Dict(keys=fields.Str(), values=fields.Dict(), required=True)
    recipe_path = fields.Str()
    dropfile_path = fields.Str()
    dlq = fields.Str()


def parse():
    if not hasattr(parse, "cache"):
        config_yml = os.environ.get("ZOCALO_CONFIG", "zocalo.yml")

        if not os.path.exists(config_yml):
            raise AttributeError(f"Cannot find config file: {config_yml}")

        with open(config_yml, "r") as stream:
            yml_dict = yaml.safe_load(stream)

            schema = ConfigSchema()
            schema.load(yml_dict, unknown=INCLUDE)

            setattr(parse, "cache", Configuration(yml_dict))

    return parse.cache


config = parse()


def transport_from_config(env):
    transport_config = config.get_plugin("stomp", env)

    for cfgoption, target in [
        ("host", "--stomp-host"),
        ("port", "--stomp-port"),
        ("password", "--stomp-pass"),
        ("username", "--stomp-user"),
        ("prefix", "--stomp-prfx"),
    ]:
        StompTransport.defaults[target] = transport_config.get(cfgoption)
