import functools
import inspect
import itertools
import keyword
import logging
import operator
import os
import pathlib
import typing

import marshmallow as mm
import pkg_resources
import yaml

from zocalo import ConfigurationError

logger = logging.getLogger("zocalo.configuration")


class ConfigSchema(mm.Schema):
    version = mm.fields.Int(required=True)
    environments = mm.fields.Dict(
        keys=mm.fields.Str(),
        values=mm.fields.Dict(
            keys=mm.fields.Str(), values=mm.fields.List(mm.fields.Str())
        ),
    )
    include = mm.fields.List(mm.fields.Str())


class PluginSchema(mm.Schema):
    plugin = mm.fields.Str(
        required=True,
        error_messages={"required": "definition lacks the mandatory 'plugin' key"},
    )


_reserved_names = {"activated", "environments", "plugin_configurations"}


def _check_valid_plugin_name(name: str) -> bool:
    valid = (
        name.isidentifier()
        and not keyword.iskeyword(name)
        and name not in _reserved_names
    )
    if not valid:
        logger.warning(
            f"Zocalo configuration plugin '{name}' is not a valid plugin name"
        )
    return valid


_configuration_plugins = {
    e.name: e
    for e in pkg_resources.iter_entry_points("zocalo.configuration.plugins")
    if _check_valid_plugin_name(e.name)
}


@functools.lru_cache(maxsize=None)
def _load_plugin(name: str):
    if name not in _configuration_plugins:
        logger.warning(f"Zocalo configuration plugin '{name}' missing")
        return False
    return _configuration_plugins[name].load()


class Configuration:
    __slots__ = tuple(
        ["_" + name for name in _configuration_plugins]
        + ["_" + name for name in _reserved_names]
    )

    def __init__(self, yaml_dict: dict):
        self._activated: typing.List[str] = []
        self._environments: typing.Dict[str, typing.List[str]] = yaml_dict.get(
            "environments", {}
        )
        self._plugin_configurations: typing.Dict[
            str, typing.Union[pathlib.Path, typing.Dict[str, typing.Any]]
        ] = {
            name: config
            for name, config in yaml_dict.items()
            if name not in ConfigSchema().fields
        }
        for name in _configuration_plugins:
            setattr(self, "_" + name, None)

    @property
    def environments(self) -> typing.Set[str]:
        return frozenset(self._environments)

    @property
    def active_environments(self) -> typing.Tuple[str]:
        return tuple(self._activated)

    def _resolve(self, plugin_configuration: str) -> bool:
        try:
            configuration = self._plugin_configurations[
                plugin_configuration
            ].read_text()
        except PermissionError as e:
            raise PermissionError(
                f"Plugin configuration {plugin_configuration} could not be resolved, "
                f"{e}"
            ) from None
        try:
            yaml_dict = yaml.safe_load(configuration)
        except yaml.MarkedYAMLError as e:
            raise ValueError(
                f"Plugin configuration {plugin_configuration} could not be resolved, "
                f"could not read {self._plugin_configurations[plugin_configuration]}: {e}"
            ) from None
        if not isinstance(yaml_dict, dict) or not yaml_dict.get("plugin"):
            raise ConfigurationError(
                f"Error reading configuration for plugin {plugin_configuration}: "
                f"Configuration file {self._plugin_configurations[plugin_configuration]} "
                "is missing a plugin specification"
            )
        self._plugin_configurations[plugin_configuration] = yaml_dict

    def activate_environment(self, name: str):
        if name not in self._environments:
            raise ValueError(f"Environment '{name}' is not defined")
        for config_name in self._environments[name]:
            logger.debug("Loading plugin configuration %s", config_name)
            if isinstance(self._plugin_configurations[config_name], pathlib.Path):
                self._resolve(config_name)
            configuration = self._plugin_configurations[config_name]
            plugin = _load_plugin(configuration["plugin"])
            if plugin:
                plugin_parameters = inspect.signature(plugin.activate).parameters
                arguments = {"configuration": configuration, "config_object": self}
                if not any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in plugin_parameters.values()
                ):
                    arguments = {
                        p: arguments[p]
                        for p in set(arguments).intersection(plugin_parameters)
                    }
                return_value = plugin.activate(**arguments)
                setattr(self, "_" + configuration["plugin"], return_value)
        self._activated.append(name)

    def __str__(self):
        environments = len(self._environments)
        plugin_configurations = len(self._plugin_configurations)
        unresolved = sum(
            1
            for conf in self._plugin_configurations.values()
            if isinstance(conf, pathlib.Path)
        )
        if unresolved:
            unresolved = f", {unresolved} of which are unresolved"
        else:
            unresolved = ""
        if not self._activated:
            activated = ""
        elif len(self._activated) == 1:
            activated = f", environment '{self._activated[0]}' activated"
        else:
            activated = f", environments {self._activated} activated"
        return f"<ZocaloConfiguration containing {environments} environments, {plugin_configurations} plugin configurations{unresolved}{activated}>"

    __repr__ = __str__


for _plugin in _configuration_plugins:
    if hasattr(Configuration, _plugin):
        logger.warning(
            f"Zocalo configuration plugin '{_plugin}' is not a valid plugin name"
        )
    else:
        setattr(Configuration, _plugin, property(operator.attrgetter("_" + _plugin)))
del _plugin


def _read_configuration_yaml(configuration: str) -> dict:
    yaml_dict = yaml.safe_load(configuration)

    if not isinstance(yaml_dict, dict) or "version" not in yaml_dict:
        raise ConfigurationError("Invalid configuration specified")
    if yaml_dict["version"] != 1:
        raise ConfigurationError(
            f"This version of Zocalo does not understand v{yaml_dict['version']} configurations"
        )

    # Convert environment shorthands: environment lists to dictionaries
    # and individual plugin configurations to single element lists
    for environment in yaml_dict.setdefault("environments", {}):
        # Convert shorthand stringsenvironment shorthand lists to dictionaries
        if isinstance(yaml_dict["environments"][environment], dict):
            pass
        elif isinstance(yaml_dict["environments"][environment], list):
            yaml_dict["environments"][environment] = {
                "plugins": yaml_dict["environments"][environment]
            }
        else:
            raise ConfigurationError(
                f"Invalid YAML configuration: Environment {environment} is not a list or dictionary"
            )
        for group in yaml_dict["environments"][environment]:
            if isinstance(yaml_dict["environments"][environment][group], list):
                pass
            elif isinstance(yaml_dict["environments"][environment][group], str):
                yaml_dict["environments"][environment][group] = [
                    yaml_dict["environments"][environment][group]
                ]
            else:
                raise ConfigurationError(
                    f"Invalid YAML configuration: Environment {environment} contains group {group} which is not a string or a list"
                )

    plugin_fields = {}
    for key in yaml_dict:
        if key in ConfigSchema().fields:
            continue
        plugin_fields[key] = mm.fields.Nested(
            PluginSchema, unknown=mm.EXCLUDE, required=True
        )
        if isinstance(yaml_dict[key], str):
            plugin_fields[key] = mm.fields.Str()
        elif isinstance(yaml_dict[key], dict) and isinstance(
            yaml_dict[key].get("plugin"), str
        ):
            plugin = _load_plugin(yaml_dict[key]["plugin"])
            if plugin and hasattr(plugin, "Schema"):
                plugin_fields[key] = mm.fields.Nested(
                    plugin.Schema, unknown=mm.EXCLUDE, required=True
                )

    class _ConfigSchema(ConfigSchema):
        class Meta:
            include = plugin_fields

    schema = _ConfigSchema()
    try:
        schema.load(yaml_dict, unknown=mm.RAISE)
    except mm.ValidationError as e:
        raise ConfigurationError(f"Invalid YAML configuration: {e}") from None

    return yaml_dict


@functools.lru_cache(maxsize=None)
def _merge_configuration(
    configuration: typing.Optional[str],
    file_: typing.Optional[pathlib.Path],
    context: pathlib.Path,
) -> dict:
    # Parse a passed YAML string or specified YAML file
    parsed_files = set()
    if file_:
        if not file_.is_file():
            raise ConfigurationError(f"Zocalo configuration file {file_} not found")
        configuration = file_.read_text()
        try:
            parsed = _read_configuration_yaml(configuration)
        except (ConfigurationError, yaml.MarkedYAMLError) as e:
            raise ConfigurationError(
                f"Error reading configuration file {file_}: {e}"
            ) from None
        parsed_files.add(file_)
    elif isinstance(configuration, str):
        parsed = _read_configuration_yaml(configuration)
    else:
        raise TypeError(
            "Either a configuration string or a configuration file must be specified"
        )

    # Resolve all lazy file references relative to the specified context parameter
    for plugin in parsed:
        if isinstance(parsed[plugin], str):
            parsed[plugin] = context.joinpath(parsed[plugin]).resolve()

    # Recursively identify and merge external files (DFS)
    if parsed.get("include"):
        for include_file in parsed["include"]:
            try:
                file_reference = context.joinpath(include_file).resolve()
                include = _read_configuration_yaml(file_reference.read_text())
                assert include
            except (ConfigurationError, yaml.MarkedYAMLError) as e:
                raise ConfigurationError(
                    f"Error reading configuration file {file_reference}: {e}"
                ) from None
        raise NotImplementedError("Importing configurations is not yet supported")

    # Flatten the data structure for each environment to a deduplicated ordered list of plugins
    for environment in parsed["environments"]:
        # First, order groups alphabetically - except 'plugins', which always comes last
        ordered_plugins = [
            parsed["environments"][environment][group]
            for group in sorted(parsed["environments"][environment])
            if group != "plugins"
        ]
        ordered_plugins.append(parsed["environments"][environment].get("plugins", []))

        # Flatten the individual lists and discard duplicates
        parsed["environments"][environment] = list(
            dict.fromkeys(itertools.chain.from_iterable(ordered_plugins))
        )

        # Ensure all referenced plugins are defined and valid
        for plugin in parsed["environments"][environment]:
            if plugin in ConfigSchema().fields:
                raise ConfigurationError(
                    f"Configuration error: environment {environment} references reserved name {plugin}"
                )
            if plugin not in parsed:
                raise ConfigurationError(
                    f"Configuration error: environment {environment} references undefined plugin {plugin}"
                )

    return parsed


def from_file(config_file=None) -> Configuration:
    if not config_file:
        config_file = os.environ.get("ZOCALO_CONFIG")
    if not config_file:
        return Configuration({})
    config_file = pathlib.Path(config_file)
    return Configuration(_merge_configuration(None, config_file, config_file.parent))


def from_string(configuration: str) -> Configuration:
    return Configuration(_merge_configuration(configuration, None, pathlib.Path.cwd()))
