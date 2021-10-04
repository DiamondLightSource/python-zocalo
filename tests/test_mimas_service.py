from unittest import mock

import workflows.transport.common_transport
from workflows.recipe.wrapper import RecipeWrapper

import zocalo.configuration
from zocalo.service.mimas import Mimas

sample_configuration = """
version: 1
mimas:
  plugin: mimas
environments:
  default: live
  live:
    mimas: mimas
"""


def generate_recipe_message(parameters, extra_params={}):
    """Helper function for tests."""
    return {
        "recipe": {
            1: {
                "service": "mimas business logic",
                "queue": "mimas",
                "parameters": parameters,
                "output": {"dispatcher": 2, "ispyb": 3},
                **extra_params,
            },
            2: {"service": "dispatcher", "queue": "transient.output"},
            3: {"service": "ispyb", "queue": "transient.output"},
            "start": [(1, [])],
        },
        "recipe-pointer": 1,
        "recipe-path": [],
        "environment": {
            "ID": mock.sentinel.GUID,
            "source": mock.sentinel.source,
            "timestamp": mock.sentinel.timestamp,
        },
        "payload": mock.sentinel.payload,
    }


def test_mimas_service(mocker, tmp_path):
    mock_transport = mock.Mock()
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate()
    mimas = Mimas(environment={"config": zc})
    setattr(mimas, "_transport", mock_transport)
    mimas.initializing()

    dcid = 12345
    testid = 12

    t = mock.create_autospec(workflows.transport.common_transport.CommonTransport)
    m = generate_recipe_message(
        parameters={
            "dcid": f"{dcid}",
            "event": "start",
            "beamline": "bl",
            "experimenttype": "Energy scan",
            "run_status": "Datacollection Successful",
        },
        extra_params={"passthrough": {"testid": testid}},
    )
    rw = RecipeWrapper(message=m, transport=t)
    send_to = mocker.spy(rw, "send_to")

    mimas.process(rw, {"some": "header"}, mock.sentinel.message)
    send_to.assert_has_calls(
        [
            mock.call(
                "dispatcher",
                {
                    "recipes": ["exafs-qa"],
                    "parameters": {"ispyb_dcid": dcid, "testid": testid},
                },
                transaction=mock.ANY,
            ),
        ]
    )
