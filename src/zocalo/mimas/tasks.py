import logging
from typing import List, Union
from abc import abstractmethod, ABC

from zocalo.mimas.classes import (
    MimasScenario,
    MimasRecipeInvocation,
    MimasISPyBJobInvocation,
)

logger = logging.getLogger(__name__)


class Tasks(ABC):
    beamline = None
    event = None
    enabled = True

    def do_run(
        self, scenario: MimasScenario,
    ) -> List[Union[MimasRecipeInvocation, MimasISPyBJobInvocation]]:

        if not self.enabled:
            logger.info("Class is currently disabled")
            return

        if self.beamline is not None:
            if scenario.beamline != self.beamline:
                logger.info("No beamline match, skipping tasks")
                return []

        if self.event is not None:
            if scenario.event != self.event:
                logger.info("No event match, skipping tasks")
                return []

        return self.run(scenario)

    @abstractmethod
    def run(
        self, scenario: MimasScenario,
    ) -> List[Union[MimasRecipeInvocation, MimasISPyBJobInvocation]]:
        pass
