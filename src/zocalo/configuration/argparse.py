from __future__ import annotations

import argparse
from typing import Iterable, List

__all__ = ["get_specified_environments"]


class _EnvParser(argparse.ArgumentParser):
    def __init__(self, *args, add_help=False, **kwargs):
        super().__init__(*args, add_help=add_help, **kwargs)

    def error(self, *args, **kwargs):
        # don't exit on error
        return None


def get_specified_environments(
    argv=None, *, arguments: Iterable[str] = ("-e", "--environment")
) -> List[str]:
    """Extract a list of all environments putatively specified on the command line.
    Returns an empty list if there are any parsing issues or there are no specified
    environments. This function is designed to be used as the first of two passes
    for parsing command line options, so that the environments can be taken into
    account when parsing all other commands."""

    env_parser = _EnvParser()
    env_parser.add_argument(
        *arguments,
        dest="envs",
        action="append",
        default=[],
    )
    selected_environments = env_parser.parse_known_args()
    if not selected_environments:
        return []

    return selected_environments[0].envs
