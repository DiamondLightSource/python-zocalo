from __future__ import annotations

import zocalo.util.symlink


def test_create_parent_symlink(tmp_path):
    d = tmp_path / "123456-uuid-7890" / "tool"
    d.mkdir(parents=True)
    assert zocalo.util.symlink.create_parent_symlink(d, "some-name") is True
    assert tmp_path.joinpath("some-name").is_symlink()
    assert tmp_path.joinpath("some-name").resolve() == d.resolve()
    assert (
        zocalo.util.symlink.create_parent_symlink(
            d, "some-name", overwrite_symlink=True
        )
        is True
    )
    assert tmp_path.joinpath("some-name").resolve() == d.resolve()

    d = tmp_path / "123456-uuid-7890" / "tool-other"
    d.mkdir()
    assert zocalo.util.symlink.create_parent_symlink(d, "some-name") is False
    assert tmp_path.joinpath("some-name").resolve() != d.resolve()
    assert (
        zocalo.util.symlink.create_parent_symlink(
            d, "some-name", overwrite_symlink=True
        )
        is True
    )
    assert tmp_path.joinpath("some-name").resolve() == d.resolve()


def test_create_parent_symlink_levels(tmp_path):
    d = tmp_path / "123456-uuid-7890" / "tool"
    d.mkdir(parents=True)
    assert zocalo.util.symlink.create_parent_symlink(d, "some-name", levels=1) is True
    assert (tmp_path / "123456-uuid-7890" / "some-name").is_symlink()
    assert (tmp_path / "123456-uuid-7890" / "some-name").resolve() == d.resolve()


def test_create_parent_symlink_does_not_overwrite_files(tmp_path):
    d = tmp_path / "123456-uuid-7890" / "tool"
    d.mkdir(parents=True)
    tmp_path.joinpath("some-name").touch()
    assert zocalo.util.symlink.create_parent_symlink(d, "some-name") is False
    assert (
        zocalo.util.symlink.create_parent_symlink(
            d, "some-name", overwrite_symlink=True
        )
        is False
    )
    assert not tmp_path.joinpath("some-name").is_symlink()
