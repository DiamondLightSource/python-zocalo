import subprocess


def test_zocalo_go_help():
    subprocess.run("zocalo.go --help", check=True, shell=True)
