import copy

from unittest import mock
from workflows.recipe import Recipe

from zocalo.system_test.common import CommonSystemTest


class DispatcherService(CommonSystemTest):
    """Tests for the dispatcher service (recipe service)."""

    def test_processing_a_trivial_recipe(self):
        """Passing in a recipe to the service without external dependencies.
        The recipe should be interpreted and a simple message passed back to a
        fixed destination."""

        recipe = self.get_recipe("test-dispatcher", load=False)
        self.send_message(
            queue="processing_recipe", message={"recipes": ["test-dispatcher"]}
        )

        self.expect_recipe_message(
            recipe=Recipe(recipe),
            recipe_path=[],
            recipe_pointer=1,
            payload=recipe["start"][0][1],
        )

    def test_parsing_a_recipe_and_replacing_parameters(self):
        """Passing in a recipe to the service without external dependencies.
        The recipe should be interpreted, the 'uuid' placeholder replaced using
        the parameter field, and the message passed back.
        The message should then contain the recipe and a correctly set pointer."""

        parameters = {"guid": self.uuid}

        recipe = self.get_recipe("test-dispatcher", load=False)
        self.send_message(
            queue="processing_recipe",
            message={"recipes": ["test-dispatcher"], "parameters": parameters},
        )

        expected_recipe = Recipe(recipe)
        expected_recipe.apply_parameters(parameters)

        self.expect_recipe_message(
            recipe=expected_recipe,
            recipe_path=[],
            recipe_pointer=1,
            payload=recipe["start"][0][1],
        )

    def test_ispyb_magic(self):
        """Test the ISPyB magic to see that it does what we think it should do"""

        recipe = self.get_recipe("test-dispatcher", load=False)
        self.send_message(
            queue="processing_recipe",
            message={
                "recipes": ["test-dispatcher"],
                "parameters": {"ispyb_dcid": self.config["dispatcher"]["ispyb_dcid"]},
            },
        )

        parameters = {"ispyb_beamline": self.config["dispatcher"]["expected_beamline"]}
        expected_recipe = Recipe(recipe)
        expected_recipe.apply_parameters(parameters)

        self.expect_recipe_message(
            recipe=expected_recipe,
            recipe_path=[],
            recipe_pointer=1,
            payload=recipe["start"][0][1],
        )

    def test_wait_for_ispyb_runstatus(self):
        """
        Test the logic to wait for a RunStatus to be set in ISPyB.
        Since we don't touch the database this should run into a timeout condition.
        """
        message = {
            "recipes": ["test-dispatcher"],
            "parameters": {
                "ispyb_dcid": 4977408,
                "ispyb_wait_for_runstatus": True,
                "dispatcher_timeout": 10,
                "dispatcher_error_queue": "transient.system_test.timeout",
            },
        }
        self.send_message(queue="processing_recipe", message=message)

        expected_recipe = self.get_recipe("test-dispatcher")
        self.expect_unreached_recipe_step(recipe=expected_recipe, recipe_pointer=1)

        # Emulate recipe mangling
        message = copy.deepcopy(message)
        message["parameters"]["uuid"] = self.uuid
        message["parameters"]["dispatcher_expiration"] = mock.ANY

        self.expect_message(
            queue="transient.system_test.timeout",
            message=message,
            min_wait=9,
            timeout=30,
        )


if __name__ == "__main__":
    DispatcherService().validate()
