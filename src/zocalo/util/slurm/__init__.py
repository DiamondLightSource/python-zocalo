from __future__ import annotations

import base64
import binascii
import json
import os
import pathlib
from typing import Any

import requests

from zocalo.configuration import Configuration

from . import models


def validate_is_jwt(token: str) -> bool:
    """Checks that a particular string is a JWT token"""
    if token.count(".") != 2:
        return False
    header, payload, _ = token.split(".")
    try:
        # Check both header and payload are valid base64-encoded json objects
        # Note that JWT are Base64URL, which might not have padding.
        if not (
            isinstance(
                json.loads(
                    base64.urlsafe_b64decode(
                        header + "=" * (4 - len(header) % 4)
                    ).decode()
                ),
                dict,
            )
            and isinstance(
                json.loads(
                    base64.urlsafe_b64decode(
                        payload + "=" * (4 - len(payload) % 4)
                    ).decode()
                ),
                dict,
            )
        ):
            return False
    except (binascii.Error, json.JSONDecodeError):
        return False

    return True


class SlurmRestApi:
    def __init__(
        self,
        url: str,
        version: str = "v0.0.40",
        user_name: str | None = None,
        user_token: str | pathlib.Path | None = None,
    ):
        self.url = url
        self.version = version
        self.user_name = user_name
        if user_token and os.path.isfile(user_token):
            with open(user_token, "r") as f:
                self.user_token = f.read().strip()
        elif isinstance(user_token, pathlib.Path):
            # We got passed a path, but it isn't a valid one
            raise RuntimeError(f"SLURM: API token file {user_token} does not exist")
        else:
            assert isinstance(user_token, str)
            if not validate_is_jwt(user_token):
                raise RuntimeError(
                    "SLURM user_token does not appear to be a valid JWT token. Did you pass a nonexistent filename?"
                )
            self.user_token = user_token
        self.session = requests.Session()
        if self.user_name:
            self.session.headers["X-SLURM-USER-NAME"] = self.user_name
        if self.user_token:
            self.session.headers["X-SLURM-USER-TOKEN"] = self.user_token

    @classmethod
    def from_zocalo_configuration(cls, zc: Configuration, cluster: str = "slurm"):
        cluster_config = getattr(zc, cluster)
        return cls(
            url=cluster_config["url"],
            version=cluster_config["api_version"],
            user_name=cluster_config.get("user"),
            user_token=cluster_config.get("user_token"),
        )

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> requests.Response:
        response = self.session.get(
            f"{self.url}/{endpoint}", params=params, timeout=timeout
        )
        response.raise_for_status()
        return response

    def put(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> requests.Response:
        response = self.session.put(
            f"{self.url}/{endpoint}", params=params, json=json, timeout=timeout
        )
        response.raise_for_status()
        return response

    def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> requests.Response:
        response = self.session.post(
            f"{self.url}/{endpoint}", data=data, json=json, timeout=timeout
        )
        response.raise_for_status()
        return response

    def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> requests.Response:
        response = self.session.delete(
            f"{self.url}/{endpoint}", params=params, timeout=timeout
        )
        response.raise_for_status()
        return response

    def get_jobs(self) -> models.OpenapiJobInfoResp:
        endpoint = f"slurm/{self.version}/jobs"
        response = self.get(endpoint)
        return models.OpenapiJobInfoResp(**response.json())

    def get_job_info(self, job_id: int) -> models.JobInfo:
        endpoint = f"slurm/{self.version}/job/{job_id}"
        response = self.get(endpoint)
        job_info_resp = models.OpenapiJobInfoResp(**response.json())
        jobinfo = next(iter(dict(job_info_resp.jobs).get("root", [])))
        return jobinfo

    def submit_job(
        self, job_submission: models.JobSubmitReq
    ) -> models.JobSubmitResponseMsg:
        endpoint = f"slurm/{self.version}/job/submit"
        response = self.post(
            endpoint, json=job_submission.model_dump(exclude_defaults=True)
        )
        return models.JobSubmitResponseMsg(**response.json())
