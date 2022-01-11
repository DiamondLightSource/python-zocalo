from __future__ import annotations

import pathlib
from typing import Union


def create_parent_symlink(
    destination_path: Union[str, pathlib.Path],
    symlink_name: str,
    *,
    levels: int = 2,
    overwrite_symlink: bool = False,
) -> bool:
    """Create a symbolic link in a parent directory,
    $levels levels above the link destination.
    If a link already exists in that location it can be overwritten.
    If a file with the symlink name exists in the location it is left
    untouched.

    :param destination_path: The full path that is the symlink destination.
    :param symlink_name: The name of the symbolic link to be created.
    :param levels: The number of levels above the destination path where the
                   symlink should be created.
    :param overwrite_symlink: If the destination exists and is a symlink,
                              whether it should be overwritten.
    :return: True if successful, False otherwise.
    """

    destination_path = pathlib.Path(destination_path)
    assert destination_path.is_absolute()
    assert levels > 0, "symlink must be in parent directory or above"

    # Generate path to the symbolic link
    link_path = destination_path.parents[levels - 1].joinpath(symlink_name)

    # Construct the (relative) destination of the symlink
    rel_destination = pathlib.Path(*destination_path.parts[-levels:])

    return symlink_to(rel_destination, link_path, overwrite_symlink=overwrite_symlink)


def symlink_to(
    link_destination: pathlib.Path,
    link_path: pathlib.Path,
    *,
    target_is_directory: bool = False,
    overwrite_symlink: bool = False,
) -> bool:
    """Create a symbolic link.
    This function works analogous to os.symlink, but optionally allows
    overwriting symbolic links, and instead of raising exceptions returns
    True on success and False on failure.
    """

    # Bail if the destination is a symbolic link and we do not overwrite links
    if link_path.is_symlink():
        # Python 3.9+: Could use .readlink() here and return True if correct
        if not overwrite_symlink:
            return False
    elif link_path.exists():
        # If it is not a symbolic link AND exists, then also bail.
        return False

    # Symlinks can't be directly overwritten, so create a temporary symlink next
    # to where it should go, and then rename on top of a potentially existing link.
    tmp_link = link_path.parent / f".tmp.{link_path.name}"
    tmp_link.symlink_to(link_destination, target_is_directory=target_is_directory)
    try:
        tmp_link.replace(link_path)
    except PermissionError as e:
        if getattr(e, "winerror", None) == 5:
            # Windows can't rename on top, so delete and retry
            link_path.unlink()
            tmp_link.replace(link_path)
        else:
            raise

    return True
