import importlib
import os
import pkgutil

import ispyb
import workflows.recipe
from workflows.services.common_service import CommonService


class Trigger(CommonService):
    """A service that creates and runs downstream processing jobs."""

    # Human readable service name
    _service_name = "Trigger"

    # Logger name
    _logger_name = "zocalo.services.trigger"

    def initializing(self):
        """Subscribe to the trigger queue. Received messages must be acknowledged."""
        workflows.recipe.wrap_subscribe(
            self._transport,
            "trigger",
            self.trigger,
            acknowledgement=True,
            log_extender=self.extend_log,
        )

        self.ispyb = ispyb.open(os.environ["ISPYB_CREDENTIALS"])

    def trigger(self, rw, header, message):
        """Forward the trigger message to a specific trigger function."""
        # Extract trigger target from the recipe
        params = rw.recipe_step.get("parameters", {})
        target = params.get("target")
        if not target:
            self.log.error("No trigger target defined in recipe")
            rw.transport.nack(header)
            return

        implementors = self.config.mimas.get("implementors", "zocalo.mimas")

        mod = importlib.import_module(f"{implementors}.implementors.triggers")
        mod = importlib.reload(mod)

        modules = {}
        for importer, modname, ispkg in pkgutil.walk_packages(
            path=mod.__path__, prefix=mod.__name__ + ".", onerror=lambda x: None
        ):
            class_name = modname.split(".")[-1]
            modules[class_name] = modname

        if target not in modules:
            self.log.error("Unknown target %s defined in recipe", target)
            rw.transport.nack(header)
            return

        txn = rw.transport.transaction_begin()
        rw.set_default_channel("output")

        def parameters(parameter, replace_variables=True):
            if isinstance(message, dict):
                base_value = message.get(parameter, params.get(parameter))
            else:
                base_value = params.get(parameter)
            if (
                not replace_variables
                or not base_value
                or not isinstance(base_value, str)
                or "$" not in base_value
            ):
                return base_value
            for key in rw.environment:
                if "$" + key in base_value:
                    base_value = base_value.replace("$" + key, str(rw.environment[key]))
            return base_value

        mod = importlib.import_module(modules[target])
        mod = importlib.reload(mod)
        cls = getattr(mod, target)
        instance = cls(
            self.ispyb,
            rw=rw,
            header=header,
            message=message,
            parameters=parameters,
            transaction=txn,
        )

        result = instance.run()
        if result.success:
            rw.send({"result": result.return_value}, transaction=txn)
            rw.transport.ack(header, transaction=txn)
        else:
            rw.transport.transaction_abort(txn)
            rw.transport.nack(header)
            return

        rw.transport.transaction_commit(txn)
