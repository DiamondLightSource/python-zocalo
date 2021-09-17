from workflows.recipe import Recipe

from zocalo.system_test.common import CommonSystemTest


class MimasService(CommonSystemTest):
    """Tests for the Mimas service."""

    def test_mimas(self):
        """Run a Mimas scenario"""

        params = self.config["mimas"]
        recipe = {
            1: {
                "service": "Mimas",
                "queue": "mimas",
                "parameters": {
                    "dcid": "1",
                    "event": params["event"],
                    "beamline": params["beamline"],
                    "experimenttype": params["experimenttype"],
                    "proposalcode": params["proposalcode"],
                    "dc_class": params["dc_class"],
                    "run_status": params["run_status"],
                },
                "output": {"dispatcher": 2, "ispyb": 2},
            },
            2: {"service": "System Test", "queue": "transient.system_test"},
            "start": [(1, [])],
        }
        recipe = Recipe(recipe)
        recipe.validate()

        self.send_message(
            queue=recipe[1]["queue"],
            message={
                "payload": recipe["start"][0][1],
                "recipe": recipe.recipe,
                "recipe-pointer": "1",
                "environment": {"ID": self.uuid},
            },
            headers={"workflows-recipe": True},
        )

        self.expect_recipe_message(
            environment={"ID": self.uuid},
            recipe=recipe,
            recipe_path=[1],
            recipe_pointer=2,
            payload={
                "recipes": [params["expected_recipe"]],
                "parameters": {"ispyb_dcid": 1},
            },
            timeout=30,
        )


if __name__ == "__main__":
    MimasService().validate()
