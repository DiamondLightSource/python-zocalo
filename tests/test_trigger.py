from unittest import mock

import workflows.transport.common_transport
from workflows.recipe.wrapper import RecipeWrapper

import zocalo.configuration
from zocalo.service.trigger import Trigger

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
                "service": "trigger",
                "queue": "trigger",
                "parameters": parameters,
                **extra_params,
            },
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


def test_trigger_service(mocker):
    mock_transport = mock.Mock()
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate()
    trigger = Trigger(environment={"config": zc})
    setattr(trigger, "_transport", mock_transport)
    trigger.initializing()

    t = mock.create_autospec(workflows.transport.common_transport.CommonTransport)
    m = generate_recipe_message(
        parameters={
            "target": "test",
            "dcid": "12345",
            "comment": "Test process",
            "automatic": True,
        },
        extra_params={"testid": 42},
    )
    rw = RecipeWrapper(message=m, transport=t)
    trigger.trigger(rw, {"some": "header"}, mock.sentinel.message)
    t.send.assert_has_calls(
        [
            mock.call(
                "processing_recipe",
                {"recipes": [], "parameters": {"ispyb_process": 12, "testid": 42}},
            ),
        ]
    )


def test_trigger_service_invalid_target(mocker):
    mock_transport = mock.Mock()
    zc = zocalo.configuration.from_string(sample_configuration)
    zc.activate()
    trigger = Trigger(environment={"config": zc})
    setattr(trigger, "_transport", mock_transport)
    trigger.initializing()

    t = mock.create_autospec(workflows.transport.common_transport.CommonTransport)
    m = generate_recipe_message(parameters={"target": "invalid", "dcid": "12345"})
    rw = RecipeWrapper(message=m, transport=t)
    trigger.trigger(rw, {"some": "header"}, mock.sentinel.message)
    t.send.assert_has_calls([])
