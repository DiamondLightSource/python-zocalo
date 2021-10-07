import logging

import workflows.transport
import zocalo.configuration


logger = logging.getLogger(__name__)


def _send_message(message: dict, headers={}):
    transport = workflows.transport.lookup(workflows.transport.default_transport)()
    try:
        transport.connect()
        transport.send("processing_recipe", message, headers=headers)
        transport.disconnect()
    except Exception:
        logger.warning("Cant connect to workflow transport")


def _get_recipe(event: str):
    zc = zocalo.configuration.from_file()
    zc.activate()

    recipe = "mimas"
    if zc.storage:
        recipe = zc.storage.get("ispyb.simulator", {}).get(event, "mimas")

    return recipe


def before(dcid: int):
    _send_message(
        {
            "recipes": [_get_recipe("recipe_before")],
            "parameters": {"ispyb_dcid": dcid, "event": "start"},
        },
    )


def after(dcid: int):
    _send_message(
        {
            "recipes": [_get_recipe("recipe_after")],
            "parameters": {"ispyb_dcid": dcid, "event": "end"},
        },
    )
