from __future__ import annotations


class Storage:
    @staticmethod
    def activate(configuration, config_object):
        storage = config_object.storage or {}
        storage.update(configuration)
        return storage
