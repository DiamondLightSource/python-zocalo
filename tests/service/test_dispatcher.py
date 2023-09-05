from __future__ import annotations

import json
from unittest import mock

import pytest
import zocalo.configuration
from workflows.recipe import Recipe
from workflows.transport.offline_transport import OfflineTransport
from zocalo.service.dispatcher import Dispatcher


@pytest.fixture
def mock_zocalo_configuration(tmp_path):
    mock_zc = mock.MagicMock(zocalo.configuration.Configuration)
    mock_zc.storage = {
        "zocalo.recipe_directory": tmp_path,
    }
    return mock_zc


@pytest.fixture
def mock_environment(mock_zocalo_configuration):
    return {"config": mock_zocalo_configuration}


@pytest.fixture
def offline_transport(mocker):
    transport = OfflineTransport()
    mocker.spy(transport, "send")
    return transport


@pytest.fixture
def example_recipe(tmp_path):
    recipe_path = tmp_path / "example-recipe.json"
    recipe_path.write_text(
        """
{
  "1": { "service": "dispatcher test",
         "queue": "{queue}"
       },
  "start": [
     [1, { "purpose": "test for zocalo dispatcher service loading a processing recipe from an external file" }]
  ]
}
"""
    )
    return recipe_path


def test_parsing_a_custom_recipe_and_replacing_parameters(
    mock_environment, offline_transport
):
    """Passing in a recipe to the service without external dependencies.
    The recipe should be interpreted, the 'food' placeholder replaced using
    the parameter field, and the message passed back.
    The message should then contain the recipe and a correctly set pointer."""
    recipe = {
        1: {
            "service": "foo",
            "queue": "bar",
            "food": "{food}",
        },
        "start": [(1, {"purpose": "trivial test for the recipe parsing service"})],
    }
    header = {
        "message-id": mock.sentinel,
        "subscription": mock.sentinel,
    }
    parameters = {"food": "spam"}
    service = Dispatcher(environment=mock_environment)
    service.transport = offline_transport
    service.start()
    service.process(
        None, header, message={"parameters": parameters, "custom_recipe": recipe}
    )
    expected_recipe = Recipe(recipe)
    expected_recipe.apply_parameters(parameters)
    expected_message = {
        "payload": recipe["start"][0][1],
        "recipe": expected_recipe.recipe,
        "recipe-path": [],
        "recipe-pointer": 1,
        "environment": mock.ANY,
    }
    offline_transport.send.assert_called_with(
        "bar",
        expected_message,
        headers={"workflows-recipe": True},
        transaction=mock.ANY,
    )


def test_loading_a_recipe_from_a_file(
    mock_environment, offline_transport, example_recipe
):
    """When a file name is passed to the service the file should be loaded and
    parsed correctly, including parameter replacement."""
    header = {
        "message-id": mock.sentinel,
        "subscription": mock.sentinel,
    }
    parameters = {"queue": "foo"}
    service = Dispatcher(environment=mock_environment)
    service.transport = offline_transport
    service.start()
    service.process(
        None,
        header,
        message={"parameters": parameters, "recipes": [example_recipe.stem]},
    )
    with example_recipe.open() as fh:
        recipe = json.load(fh)
    expected_recipe = Recipe(recipe)
    expected_recipe.apply_parameters(parameters)
    expected_message = {
        "payload": recipe["start"][0][1],
        "recipe": expected_recipe.recipe,
        "recipe-path": [],
        "recipe-pointer": 1,
        "environment": mock.ANY,
    }
    offline_transport.send.assert_called_with(
        "foo",
        expected_message,
        headers={"workflows-recipe": True},
        transaction=mock.ANY,
    )


def test_combining_recipes(mock_environment, offline_transport, example_recipe):
    """Combine a recipe from a file and a custom recipe."""
    header = {
        "message-id": mock.sentinel,
        "subscription": mock.sentinel,
    }
    parameters = {"queue": "foo"}
    custom_recipe = {
        1: {"service": "dispatcher test", "queue": "bar"},
        "start": [(1, {"purpose": "test recipe merging"})],
    }
    message = {
        "parameters": parameters,
        "recipes": [example_recipe.stem],
        "custom_recipe": custom_recipe,
    }
    service = Dispatcher(environment=mock_environment)
    service.transport = offline_transport
    service.start()
    service.process(None, header=header, message=message)
    with example_recipe.open() as fh:
        recipe = json.load(fh)
    expected_recipe = Recipe(recipe)
    expected_recipe.apply_parameters(parameters)
    common_expected_message = {
        "recipe": mock.ANY,
        "recipe-path": [],
        "environment": mock.ANY,
    }
    offline_transport.send.assert_has_calls(
        [
            mock.call(
                "bar",
                {
                    **common_expected_message,
                    "recipe-pointer": 1,
                    "payload": custom_recipe["start"][0][1],
                },
                headers={"workflows-recipe": True},
                transaction=mock.ANY,
            ),
            mock.call(
                "foo",
                {
                    **common_expected_message,
                    "recipe-pointer": 2,
                    "payload": recipe["start"][0][1],
                },
                headers={"workflows-recipe": True},
                transaction=mock.ANY,
            ),
        ],
        any_order=True,
    )
