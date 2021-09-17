import dataclasses
import enum
import functools
import numbers
from typing import Tuple

import gemmi


MimasExperimentType = enum.Enum(
    "MimasExperimentType",
    "OSC MESH SAD ENERGY_SCAN XRF_MAP XRF_MAP_XAS XRF_SPECTRUM UNDEFINED",
)

# enum.Enum(
#     "SAD",
#     "SAD - Inverse Beam",
#     "OSC",
#     "Collect - Multiwedge",
#     "MAD",
#     "Helical",
#     "Multi-positional",
#     "Mesh",
#     "Burn",
#     "MAD - Inverse Beam",
#     "Characterization",
#     "Dehydration",
#     "tomo",
#     "experiment",
#     "EM",
#     "PDF",
#     "PDF+Bragg",
#     "Bragg",
#     "single particle",
#     "Serial Fixed",
#     "Serial Jet",
#     "Standard",
#     "Time Resolved",
#     "Diamond Anvil High Pressure",
#     "Custom",
#     "XRF map",
#     "Energy scan",
#     "XRF spectrum",
#     "XRF map xas",
# )

MimasDCClass = enum.Enum("MimasDCClass", "GRIDSCAN ROTATION SCREENING UNDEFINED")

MimasDetectorClass = enum.Enum("MimasDetectorClass", "PILATUS EIGER")

MimasEvent = enum.Enum("MimasEvent", "START END")

MimasRunStatus = enum.Enum("MimasRunStatus", "SUCCESS FAILURE UNKNOWN")


@dataclasses.dataclass(frozen=True)
class MimasISPyBUnitCell:
    a: float
    b: float
    c: float
    alpha: float
    beta: float
    gamma: float

    @property
    def string(self):
        return f"{self.a},{self.b},{self.c},{self.alpha},{self.beta},{self.gamma}"


@dataclasses.dataclass(frozen=True)
class MimasISPyBSpaceGroup:
    symbol: str

    @property
    def string(self):
        return gemmi.SpaceGroup(self.symbol).hm.replace(" ", "")


@dataclasses.dataclass(frozen=True)
class MimasISPyBSweep:
    dcid: int
    start: int
    end: int


@dataclasses.dataclass(frozen=True)
class MimasScenario:
    dcid: int
    experimenttype: MimasExperimentType
    event: MimasEvent
    beamline: str
    runstatus: MimasRunStatus
    dcclass: MimasDCClass = None
    spacegroup: MimasISPyBSpaceGroup = None
    unitcell: MimasISPyBUnitCell = None
    getsweepslistfromsamedcg: Tuple[MimasISPyBSweep] = ()
    preferred_processing: str = None
    detectorclass: MimasDetectorClass = None
    proposalcode: str = None


@dataclasses.dataclass(frozen=True)
class MimasISPyBParameter:
    key: str
    value: str


@dataclasses.dataclass(frozen=True)
class MimasISPyBTriggerVariable:
    key: str
    value: str


@dataclasses.dataclass(frozen=True)
class MimasISPyBJobInvocation:
    dcid: int
    autostart: bool
    recipe: str
    source: str
    comment: str = ""
    displayname: str = ""
    parameters: Tuple[MimasISPyBParameter] = ()
    sweeps: Tuple[MimasISPyBSweep] = ()
    triggervariables: Tuple[MimasISPyBTriggerVariable] = ()


@dataclasses.dataclass(frozen=True)
class MimasRecipeInvocation:
    dcid: int
    recipe: str


@functools.singledispatch
def validate(mimasobject, expectedtype=None):
    """
    A generic validation function that can (recursively) validate any Mimas*
    object for consistency and semantic correctness.
    If any issues are found a ValueError is raised, returns None otherwise.
    """
    raise ValueError(f"{mimasobject!r} is not a known Mimas object")


@validate.register(MimasScenario)
def _(mimasobject: MimasScenario, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")
    if type(mimasobject.dcid) != int:
        raise ValueError(f"{mimasobject!r} has non-integer dcid")
    validate(mimasobject.experimenttype, expectedtype=MimasExperimentType)
    validate(mimasobject.runstatus, expectedtype=MimasRunStatus)
    if mimasobject.dcclass is not None:
        validate(mimasobject.dcclass, expectedtype=MimasDCClass)
    validate(mimasobject.event, expectedtype=MimasEvent)
    if type(mimasobject.getsweepslistfromsamedcg) not in (list, tuple):
        raise ValueError(
            f"{mimasobject!r} getsweepslistfromsamedcg must be a tuple, not {type(mimasobject.getsweepslistfromsamedcg)}"
        )
    for sweep in mimasobject.getsweepslistfromsamedcg:
        validate(sweep, expectedtype=MimasISPyBSweep)
    if mimasobject.unitcell is not None:
        validate(mimasobject.unitcell, expectedtype=MimasISPyBUnitCell)
    if mimasobject.spacegroup is not None:
        validate(mimasobject.spacegroup, expectedtype=MimasISPyBSpaceGroup)
    if mimasobject.detectorclass is not None:
        validate(mimasobject.detectorclass, expectedtype=MimasDetectorClass)


@validate.register(MimasExperimentType)
def _(mimasobject: MimasExperimentType, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")


@validate.register(MimasRunStatus)
def _(mimasobject: MimasRunStatus, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")


@validate.register(MimasEvent)
def _(mimasobject: MimasEvent, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")


@validate.register(MimasDCClass)
def _(mimasobject: MimasDCClass, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")


@validate.register(MimasDetectorClass)
def _(mimasobject: MimasDetectorClass, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")


@validate.register(MimasRecipeInvocation)
def _(mimasobject: MimasRecipeInvocation, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")
    if type(mimasobject.dcid) != int:
        raise ValueError(f"{mimasobject!r} has non-integer dcid")
    if type(mimasobject.recipe) != str:
        raise ValueError(f"{mimasobject!r} has non-string recipe")
    if not mimasobject.recipe:
        raise ValueError(f"{mimasobject!r} has empty recipe string")


@validate.register(MimasISPyBJobInvocation)
def _(mimasobject: MimasISPyBJobInvocation, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")
    if type(mimasobject.dcid) != int:
        raise ValueError(f"{mimasobject!r} has non-integer dcid")
    if mimasobject.autostart not in (True, False):
        raise ValueError(f"{mimasobject!r} has invalid autostart property")
    if type(mimasobject.parameters) not in (list, tuple):
        raise ValueError(
            f"{mimasobject!r} parameters must be a tuple, not {type(mimasobject.parameters)}"
        )
    for parameter in mimasobject.parameters:
        validate(parameter, expectedtype=MimasISPyBParameter)
    if type(mimasobject.recipe) != str:
        raise ValueError(f"{mimasobject!r} has non-string recipe")
    if not mimasobject.recipe:
        raise ValueError(f"{mimasobject!r} has empty recipe string")
    if type(mimasobject.sweeps) not in (list, tuple):
        raise ValueError(
            f"{mimasobject!r} sweeps must be a tuple, not {type(mimasobject.sweeps)}"
        )
    for sweep in mimasobject.sweeps:
        validate(sweep, expectedtype=MimasISPyBSweep)


@validate.register(MimasISPyBParameter)
def _(mimasobject: MimasISPyBParameter, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")
    if type(mimasobject.key) != str:
        raise ValueError(f"{mimasobject!r} has non-string key")
    if not mimasobject.key:
        raise ValueError(f"{mimasobject!r} has an empty key")
    if type(mimasobject.value) != str:
        raise ValueError(
            f"{mimasobject!r} value must be a string, not {type(mimasobject.value)}"
        )


@validate.register(MimasISPyBSweep)
def _(mimasobject: MimasISPyBSweep, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")
    if type(mimasobject.dcid) != int:
        raise ValueError(f"{mimasobject!r} has non-integer dcid")
    if mimasobject.dcid <= 0:
        raise ValueError(f"{mimasobject!r} has an invalid dcid")
    if type(mimasobject.start) != int:
        raise ValueError(f"{mimasobject!r} has non-integer start image")
    if mimasobject.start <= 0:
        raise ValueError(f"{mimasobject!r} has an invalid start image")
    if type(mimasobject.end) != int:
        raise ValueError(f"{mimasobject!r} has non-integer end image")
    if mimasobject.end < mimasobject.start:
        raise ValueError(f"{mimasobject!r} has an invalid end image")


@validate.register(MimasISPyBUnitCell)
def _(mimasobject: MimasISPyBUnitCell, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")
    if not isinstance(mimasobject.a, numbers.Real) or mimasobject.a <= 0:
        raise ValueError(f"{mimasobject!r} has invalid length a")
    if not isinstance(mimasobject.b, numbers.Real) or mimasobject.b <= 0:
        raise ValueError(f"{mimasobject!r} has invalid length b")
    if not isinstance(mimasobject.c, numbers.Real) or mimasobject.c <= 0:
        raise ValueError(f"{mimasobject!r} has invalid length c")
    if (
        not isinstance(mimasobject.alpha, numbers.Real)
        or not 0 < mimasobject.alpha < 180
    ):
        raise ValueError(f"{mimasobject!r} has invalid angle alpha")
    if not isinstance(mimasobject.beta, numbers.Real) or not 0 < mimasobject.beta < 180:
        raise ValueError(f"{mimasobject!r} has invalid angle beta")
    if (
        not isinstance(mimasobject.gamma, numbers.Real)
        or not 0 < mimasobject.gamma < 180
    ):
        raise ValueError(f"{mimasobject!r} has invalid angle gamma")


@validate.register(MimasISPyBSpaceGroup)
def _(mimasobject: MimasISPyBSpaceGroup, expectedtype=None):
    if expectedtype and not isinstance(mimasobject, expectedtype):
        raise ValueError(f"{mimasobject!r} is not a {expectedtype}")
    gemmi.SpaceGroup(mimasobject.symbol)


@functools.singledispatch
def zocalo_message(mimasobject):
    """
    A generic function that (recursively) transforms any Mimas* object
    into serializable objects that can be sent via zocalo.
    If any issues are found a ValueError is raised.
    """
    if isinstance(mimasobject, (bool, int, float, str, type(None))):
        # trivial base types
        return mimasobject
    raise ValueError(f"{mimasobject!r} is not a known Mimas object")


@zocalo_message.register(MimasRecipeInvocation)
def _(mimasobject: MimasRecipeInvocation):
    return {
        "recipes": [mimasobject.recipe],
        "parameters": {"ispyb_dcid": mimasobject.dcid},
    }


@zocalo_message.register(MimasISPyBJobInvocation)
def _(mimasobject: MimasISPyBJobInvocation):
    return dataclasses.asdict(mimasobject)


@zocalo_message.register(MimasISPyBSweep)
def _(mimasobject: MimasISPyBSweep):
    return dataclasses.asdict(mimasobject)


@zocalo_message.register(MimasISPyBParameter)
def _(mimasobject: MimasISPyBParameter):
    return dataclasses.asdict(mimasobject)


@zocalo_message.register(MimasISPyBUnitCell)
def _(mimasobject: MimasISPyBUnitCell):
    return dataclasses.astuple(mimasobject)


@zocalo_message.register(MimasISPyBSpaceGroup)
def _(mimasobject: MimasISPyBSpaceGroup):
    return mimasobject.string


@zocalo_message.register(list)
def _(list_: list):
    return [zocalo_message(element) for element in list_]


@zocalo_message.register(tuple)
def _(tuple_: tuple):
    return tuple(zocalo_message(element) for element in tuple_)


@functools.singledispatch
def zocalo_command_line(mimasobject):
    """
    Return the command line equivalent to execute a given Mimas* object
    """
    raise ValueError(f"{mimasobject!r} is not a known Mimas object")


@zocalo_command_line.register(MimasRecipeInvocation)
def _(mimasobject: MimasRecipeInvocation):
    return f"zocalo.go -r {mimasobject.recipe} {mimasobject.dcid}"


@zocalo_command_line.register(MimasISPyBJobInvocation)
def _(mimasobject: MimasISPyBJobInvocation):
    if mimasobject.comment:
        comment = f"--comment={mimasobject.comment!r} "
    else:
        comment = ""
    if mimasobject.displayname:
        displayname = f"--display={mimasobject.displayname!r} "
    else:
        displayname = ""
    parameters = " ".join(
        f"--add-param={p.key}:{p.value}" for p in mimasobject.parameters
    )
    sweeps = " ".join(
        f"--add-sweep={s.dcid}:{s.start}:{s.end}" for s in mimasobject.sweeps
    )
    if mimasobject.autostart:
        trigger = "--trigger "
    else:
        trigger = ""
    triggervars = " ".join(
        f"--trigger-variable={tv.key}:{tv.value}" for tv in mimasobject.triggervariables
    )

    return (
        f"ispyb.job --new --dcid={mimasobject.dcid} --source={mimasobject.source} --recipe={mimasobject.recipe} "
        f"{sweeps} {parameters} {displayname}{comment}{trigger}{triggervars}"
    )
