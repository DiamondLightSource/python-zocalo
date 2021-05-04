import pkg_resources
from marshmallow import INCLUDE, Schema, ValidationError


class PluginSchema(Schema):
    pass


class Plugin(dict):
    schema = None

    def __init__(self, initial_dict):
        if self.schema:
            try:
                self.schema.load(initial_dict, unknown=INCLUDE)
            except ValidationError:
                print(f"Error loading configuration plugin: {initial_dict['plugin']}")
                raise

        super().__init__(initial_dict)


def get_known_plugins():
    if not hasattr(get_known_plugins, "cache"):
        setattr(
            get_known_plugins,
            "cache",
            {
                e.name: e.load()
                for e in pkg_resources.iter_entry_points("zocalo.configuration.plugins")
            },
        )
    register = get_known_plugins.cache.copy()
    return register
