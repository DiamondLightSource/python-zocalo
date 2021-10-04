import importlib
import pkgutil
import logging
from typing import List, Union

from zocalo.mimas.classes import (
    MimasScenario,
    MimasRecipeInvocation,
    MimasISPyBJobInvocation,
)
from zocalo.mimas.tasks import Tasks

logger = logging.getLogger(__name__)


def load(mod_file: str, cls_name: str) -> Tasks:
    mod = importlib.import_module(mod_file)
    mod = importlib.reload(mod)
    return getattr(mod, cls_name)


def run(
    scenario: MimasScenario,
    implementors=None,
) -> List[Union[MimasRecipeInvocation, MimasISPyBJobInvocation]]:
    tasks = []

    if implementors is None:
        implementors = "zocalo.mimas"

    mod = importlib.import_module(f"{implementors}.implementors.tasks")
    mod = importlib.reload(mod)

    classes = []
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=mod.__path__, prefix=mod.__name__ + ".", onerror=lambda x: None
    ):
        try:
            class_name = modname.split(".")[-1]
            classes.append(load(modname, class_name))
        except AttributeError:
            logger.error(
                f"Implementor for '{modname}' module does not contain class '{class_name}'"
            )
        except Exception:
            logger.exception(f"Could not load mimas task class {mod}")

    if not classes:
        logger.warning("No processing classes found")

    for cls in classes:
        try:
            instance = cls()
            tasks.extend(instance.do_run(scenario))
        except Exception:
            logger.exception(f"Could not run mimas task class {cls.__name__}")

    return tasks
