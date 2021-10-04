import subprocess
import sys


def test_zocalo_wrap_help():
    subprocess.run(("zocalo.wrap", "--help"), check=True, shell=sys.platform == "win32")
