class Storage:
    @staticmethod
    def activate(configuration, config_object):
        if not hasattr(config_object, "storage"):
            config_object.storage = {}
        config_object.storage.update(configuration)
