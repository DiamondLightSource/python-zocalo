import subprocess


def test_zocalo_wrap_help():
    subprocess.run(("zocalo.wrap", "--help"), check=True)
