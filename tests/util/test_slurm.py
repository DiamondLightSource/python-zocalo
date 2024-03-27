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
        "api_version": "v0.0.40",
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
                "account": "acc",
                "accrue_time": {"infinite": False, "number": 0, "set": True},
                "admin_comment": "",
                "allocating_node": "vse-200",
                "array_job_id": {"infinite": False, "number": 6077609, "set": True},
                "array_max_tasks": {"infinite": False, "number": 2, "set": True},
                "array_task_id": {"infinite": False, "number": 41, "set": True},
                "array_task_string": "",
                "association_id": 1845,
                "batch_features": "",
                "batch_flag": True,
                "batch_host": "cma2-2",
                "billable_tres": {"infinite": False, "number": 1.0, "set": True},
                "burst_buffer": "",
                "burst_buffer_state": "",
                "cluster": "cluster",
                "cluster_features": "",
                "command": "cjb_arch.sh",
                "comment": "",
                "container": "",
                "container_id": "",
                "contiguous": False,
                "core_spec": 0,
                "cores_per_socket": {"infinite": False, "number": 0, "set": False},
                "cpu_frequency_governor": {
                    "infinite": False,
                    "number": 0,
                    "set": False,
                },
                "cpu_frequency_maximum": {"infinite": False, "number": 0, "set": False},
                "cpu_frequency_minimum": {"infinite": False, "number": 0, "set": False},
                "cpus": {"infinite": False, "number": 1, "set": True},
                "cpus_per_task": {"infinite": False, "number": 1, "set": True},
                "cpus_per_tres": "",
                "cron": "",
                "current_working_directory": "/home/acc",
                "deadline": {"infinite": False, "number": 0, "set": True},
                "delay_boot": {"infinite": False, "number": 0, "set": True},
                "dependency": "",
                "derived_exit_code": {
                    "return_code": {"infinite": False, "number": 0, "set": True},
                    "signal": {
                        "id": {"infinite": False, "number": 0, "set": False},
                        "name": "",
                    },
                    "status": ["SUCCESS"],
                },
                "eligible_time": {"infinite": False, "number": 1711534808, "set": True},
                "end_time": {"infinite": False, "number": 1712226008, "set": True},
                "excluded_nodes": "",
                "exclusive": [],
                "exit_code": {
                    "return_code": {"infinite": False, "number": 0, "set": True},
                    "signal": {
                        "id": {"infinite": False, "number": 0, "set": False},
                        "name": "",
                    },
                    "status": ["SUCCESS"],
                },
                "extra": "",
                "failed_node": "",
                "features": "",
                "federation_origin": "",
                "federation_siblings_active": "",
                "federation_siblings_viable": "",
                "flags": [
                    "JOB_WAS_RUNNING",
                    "USING_DEFAULT_QOS",
                    "USING_DEFAULT_WCKEY",
                ],
                "gres_detail": [],
                "group_id": 37524,
                "group_name": "acc",
                "het_job_id": {"infinite": False, "number": 0, "set": True},
                "het_job_id_set": "",
                "het_job_offset": {"infinite": False, "number": 0, "set": True},
                "job_id": 6080221,
                "job_resources": {
                    "allocated_cores": 1,
                    "allocated_cpus": 0,
                    "allocated_hosts": 1,
                    "allocated_nodes": [
                        {
                            "cpus_used": 0,
                            "memory_allocated": 9000,
                            "memory_used": 0,
                            "nodename": "cma2-02",
                            "sockets": {"0": {"cores": {"8": "allocated"}}},
                        }
                    ],
                    "nodes": "cma2-02",
                },
                "job_size_str": [],
                "job_state": ["RUNNING"],
                "last_sched_evaluation": {
                    "infinite": False,
                    "number": 1711534808,
                    "set": True,
                },
                "licenses": "",
                "mail_type": [],
                "mail_user": "acc",
                "max_cpus": {"infinite": False, "number": 0, "set": True},
                "max_nodes": {"infinite": False, "number": 0, "set": True},
                "maximum_switch_wait_time": 0,
                "mcs_label": "",
                "memory_per_cpu": {"infinite": False, "number": 9000, "set": True},
                "memory_per_node": {"infinite": False, "number": 0, "set": False},
                "memory_per_tres": "",
                "minimum_cpus_per_node": {"infinite": False, "number": 1, "set": True},
                "minimum_switches": 0,
                "minimum_tmp_disk_per_node": {
                    "infinite": False,
                    "number": 0,
                    "set": True,
                },
                "name": "archive",
                "network": "",
                "nice": 0,
                "node_count": {"infinite": False, "number": 1, "set": True},
                "nodes": "cma2-02",
                "oversubscribe": True,
                "partition": "cs",
                "power": {"flags": []},
                "pre_sus_time": {"infinite": False, "number": 0, "set": True},
                "preempt_time": {"infinite": False, "number": 0, "set": True},
                "preemptable_time": {"infinite": False, "number": 0, "set": True},
                "prefer": "",
                "priority": {"infinite": False, "number": 1, "set": True},
                "profile": ["NOT_SET"],
                "qos": "normal",
                "reboot": False,
                "requeue": True,
                "required_nodes": "",
                "resize_time": {"infinite": False, "number": 0, "set": True},
                "restart_cnt": 0,
                "resv_name": "",
                "scheduled_nodes": "",
                "selinux_context": "",
                "shared": [],
                "show_flags": ["ALL", "DETAIL", "LOCAL"],
                "sockets_per_board": 0,
                "sockets_per_node": {"infinite": False, "number": 0, "set": False},
                "standard_error": "archive_6077609-41.err",
                "standard_input": "/dev/null",
                "standard_output": "archive_6077609-41.out",
                "start_time": {"infinite": False, "number": 1711534808, "set": True},
                "state_description": "",
                "state_reason": "None",
                "submit_time": {"infinite": False, "number": 1711533827, "set": True},
                "suspend_time": {"infinite": False, "number": 0, "set": True},
                "system_comment": "",
                "tasks": {"infinite": False, "number": 1, "set": True},
                "tasks_per_board": {"infinite": False, "number": 0, "set": True},
                "tasks_per_core": {"infinite": True, "number": 0, "set": False},
                "tasks_per_node": {"infinite": False, "number": 0, "set": True},
                "tasks_per_socket": {"infinite": True, "number": 0, "set": False},
                "tasks_per_tres": {"infinite": False, "number": 0, "set": True},
                "thread_spec": 32766,
                "threads_per_core": {"infinite": False, "number": 0, "set": False},
                "time_limit": {"infinite": False, "number": 11520, "set": True},
                "time_minimum": {"infinite": False, "number": 0, "set": True},
                "tres_alloc_str": "cpu=1,mem=9000M,node=1,billing=1",
                "tres_bind": "",
                "tres_freq": "",
                "tres_per_job": "",
                "tres_per_node": "",
                "tres_per_socket": "",
                "tres_per_task": "",
                "tres_req_str": "cpu=1,mem=9000M,node=1,billing=1",
                "user_id": 37524,
                "user_name": "acc",
                "wckey": "",
            }
        ],
        "last_backfill": {"infinite": False, "number": 1711536308, "set": True},
        "last_update": {"infinite": False, "number": 1711536388, "set": True},
        "meta": {
            "client": {"group": "root", "source": "[localhost]:51114", "user": "root"},
            "command": [],
            "plugin": {
                "accounting_storage": "acc_st/slurmdbd",
                "data_parser": "data_parser/v0.0.40",
                "name": "Slurm OpenAPI slurmctld",
                "type": "openapi/slurmctld",
            },
            "slurm": {
                "cluster": "cluster",
                "release": "23.11.1",
                "version": {"major": "23", "micro": "1", "minor": "11"},
            },
        },
        "warnings": [],
    }


def test_get_slurm_api_from_zocalo_configuration(slurm_api):
    assert slurm_api.url == "http://slurm.example.com:1234"
    assert slurm_api.version == "v0.0.40"
    assert slurm_api.user_name == "foo"
    assert slurm_api.user_token == "sometoken"


def test_get_slurm_api_user_token_external_file(tmp_path):
    user_token_file = tmp_path / "slurm-user-token"
    user_token_file.write_text("foobar")
    api = slurm.SlurmRestApi(
        url="http://slurm.example.com:1234",
        version="v0.0.40",
        user_name="foo",
        user_token=user_token_file,
    )
    assert api.user_token == "foobar"


def test_get_jobs(requests_mock, slurm_api, jobs_response):
    requests_mock.get(
        "/slurm/v0.0.40/jobs",
        json=jobs_response,
    )
    assert slurm_api.get_jobs() == slurm.models.OpenapiJobInfoResp(**jobs_response)


def test_get_job_info(requests_mock, slurm_api, jobs_response):
    requests_mock.get(
        "/slurm/v0.0.40/job/129",
        json=jobs_response,
    )
    assert slurm_api.get_job_info(129) == next(
        iter(
            dict(slurm.models.OpenapiJobInfoResp(**jobs_response).jobs).get(
                "__root__", []
            )
        )
    )
