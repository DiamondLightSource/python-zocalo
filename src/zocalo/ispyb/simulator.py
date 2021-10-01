import logging

import workflows.transport
import zocalo.configuration
from zocalo.configuration import Configuration


logger = logging.getLogger(__name__)


def send_message(zc: Configuration, message: dict, headers={}):
    if (
        zc.storage
        and zc.storage.get("zocalo.default_transport")
        in workflows.transport.get_known_transports()
    ):
        transport_type = zc.storage["zocalo.default_transport"]
    else:
        transport_type = workflows.transport.default_transport

    transport = workflows.transport.lookup(transport_type)()
    try:
        transport.connect()
        transport.send("processing_recipe", message, headers=headers)
        transport.disconnect()
    except Exception:
        logger.warning("Cant connect to workflow transport")


def before(dcid: int):
    zc = zocalo.configuration.from_file()
    zc.activate()

    default_recipe = "mimas"
    if zc.storage:
        recipe = zc.storage.get("ispyb.simulator", {}).get("recipe_before", "mimas")
    else:
        recipe = default_recipe

    send_message(
        zc,
        message={
            "recipes": [recipe],
            "parameters": {"ispyb_dcid": dcid, "event": "start"},
        },
    )


def after(dcid: int):
    zc = zocalo.configuration.from_file()
    zc.activate()

    default_recipe = "mimas"
    if zc.storage:
        recipe = zc.storage.get("ispyb.simulator", {}).get("recipe_after", "mimas")
    else:
        recipe = default_recipe

    send_message(
        zc,
        {
            "recipes": [recipe],
            "parameters": {"ispyb_dcid": dcid, "event": "end"},
        },
    )
