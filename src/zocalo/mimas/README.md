# Mimas: a zocalo decision making service

Mimas includes the following services:

* Mimas - the decision maker
* Trigger - a downstream trigger service (for starting jobs after another has finished)

CLI tools:

* zocalo.mimas - interrogate a specific dcid for the expected execution plan

## Installation

Cookiecutter the local implementation project:

```python
pip install cookiecutter
cookiecutter https://github.com/DiamondLightSource/python-zocalo/implementors
cd mimas_<name>
pip install -e .
```

Then set the new package as the mimas implementors:

```yaml
mimas:
  plugin: mimas
  implementors: mimas_<name>
```

## Tasks

Multiple task files can be created in the implementors.tasks module. These tell mimas what to do, an example is provided. All classes should inherit from `Tasks`. If `beamline` is specified this class will only be run if the scenario specifies the beamline. `event` can also be specified to run this class only on a specific event. Classes should be named the same as the file. The `run` method should return a list of `MimasRecipeInvocation` or `MimasISPyBJobInvocation`.

```python
file: mimas_<name>/implementors/tasks/mybeamline.py

from zocalo.mimas.tasks import Tasks
from zocalo.mimas.classes import (
    MimasExperimentType,
    MimasRecipeInvocation,
    MimasISPyBJobInvocation,
    MimasEvent,
)


class mybeamline(Tasks):
    beamline = "bl"
    event = MimasEvent.START

    def run(self, scenario):
        tasks = []

        if scenario.experimenttype == MimasExperimentType.ENERGY_SCAN:
            tasks.append(
                MimasRecipeInvocation(dcid=scenario.dcid, recipe="myrecipe")
            )

        return tasks
```

## Triggers

Downstream triggers are defined in a similar way to tasks.

A recipe as follows:
```yaml
{
  "1": {
    "service": "Trigger",
    "queue": "trigger",
    "parameters": {
      "target": "test",
      ...
    }
  },
  "start": [[1, []]]
}
```

will cause the trigger service to search for a module called `test` in the `implementors.triggers` package. The class should be named the same as the file. The `run` function should return an instance of `TriggerResponse`.

```python
file: mimas_<name>/implementors/triggers/test.py

from zocalo.trigger import Trigger, TriggerResponse


class test(Trigger):
    name = "TestTrigger"

    def run(self):
        self._jobid = 12
        self._trigger_job({"testid": 42})

        return TriggerResponse(success=True, return_value=self._jobid)
```

## System Test

Required configuration for associated system test

```yaml
storage:
  plugin: storage

  system_tests:
    mimas:
      event: start
      beamline: bl
      experimenttype: Energy scan
      proposalcode: bl
      dc_class: 
        grid: None
        screen: None
        rotation: None
      run_status: Successful
      expected_recipe: exafs-qa
```
