from __future__ import annotations

import pytest

import zocalo.configuration
from zocalo.util import slurm


@pytest.fixture
def zocalo_configuration(mocker):
    zc = mocker.MagicMock(zocalo.configuration.Configuration)
    zc.slurm = {
        "url": "http://slurm.example.com:1234",
        "user": "foo",
        "user_token": "sometoken",
        "api_version": "v0.0.36",
    }
    return zc


@pytest.fixture
def slurm_api(zocalo_configuration):
    api = slurm.SlurmRestApi.from_zocalo_configuration(zocalo_configuration)
    return api


@pytest.fixture
def jobs_response():
    return {
        "errors": [],
        "jobs": [
            {
                "batch_host": "cs04r-sc-com13-01",
                "flags": ["JOB_WAS_RUNNING"],
                "cluster": "cluster",
                "command": "bash",
                "eligible_time": "1675327225",
                "end_time": "1706863225",
                "exit_code": 0,
                "group_id": "12345",
                "job_id": "129",
                "job_resources": {
                    "nodes": "cs04r-sc-com13-01",
                    "allocated_cpus": 1,
                    "allocated_hosts": 1,
                    "allocated_nodes": {
                        "0": {
                            "memory": 0,
                            "cpus": 1,
                            "sockets": {"0": "unassigned"},
                            "cores": {"0": "unassigned"},
                        }
                    },
                },
                "job_state": "RUNNING",
                "last_sched_evaluation": "1675327225",
                "max_cpus": "0",
                "max_nodes": "0",
                "name": "bash",
                "nodes": "cs04r-sc-com13-01",
                "tasks_per_board": "0",
                "cpus": "1",
                "node_count": "1",
                "tasks": "1",
                "partition": "wilson",
                "minimum_cpus_per_node": "1",
                "minimum_tmp_disk_per_node": "0",
                "priority": "4294901730",
                "qos": "normal",
                "start_time": "1675327225",
                "submit_time": "1675327225",
                "user_id": "123456",
                "user_name": "foo",
                "current_working_directory": "/home/foo",
            }
        ],
    }


def test_get_slurm_api_from_zocalo_configuration(slurm_api):
    assert slurm_api.url == "http://slurm.example.com:1234"
    assert slurm_api.version == "v0.0.36"
    assert slurm_api.user_name == "foo"
    assert slurm_api.user_token == "sometoken"


def test_get_slurm_api_user_token_external_file(tmp_path):
    user_token_file = tmp_path / "slurm-user-token"
    user_token_file.write_text("foobar")
    api = slurm.SlurmRestApi(
        url="http://slurm.example.com:1234",
        version="v0.0.36",
        user_name="foo",
        user_token=user_token_file,
    )
    assert api.user_token == "foobar"


def test_get_jobs(requests_mock, slurm_api, jobs_response):
    requests_mock.get(
        "/slurm/v0.0.36/jobs",
        json=jobs_response,
    )
    assert slurm_api.get_jobs() == slurm.models.JobsResponse(**jobs_response)


def test_get_job_info(requests_mock, slurm_api, jobs_response):
    requests_mock.get(
        "/slurm/v0.0.36/job/129",
        json=jobs_response,
    )
    assert slurm_api.get_job_info(129) == slurm.models.JobsResponse(**jobs_response)
