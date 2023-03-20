from __future__ import annotations

from typing import Any, Optional

import requests

import zocalo.configuration

from . import models


class SlurmRestApi:
    def __init__(
        self,
        url: str,
        version: str = "v0.0.36",
        user_name: Optional[str] = None,
        user_token: Optional[str] = None,
    ):
        self._url = url
        self._version = version
        self._session = requests.Session()
        if user_name:
            self._session.headers["X-SLURM-USER-NAME"] = user_name
        if user_token:
            self._session.headers["X-SLURM-USER-TOKEN"] = user_token

    @classmethod
    def from_zocalo_configuration(cls, zc: zocalo.configuration.Configuration):
        return cls(
            url=zc.slurm["url"],
            version=zc.slurm["api_version"],
            user_name=zc.slurm.get("user"),
            user_token=zc.slurm.get("user_token"),
        )

    def get(
        self, endpoint: str, params: dict[str, Any] = None, timeout: float | None = None
    ) -> requests.Response:
        response = self._session.get(
            f"{self._url}/{endpoint}", params=params, timeout=timeout
        )
        response.raise_for_status()
        return response

    def put(
        self,
        endpoint: str,
        params: dict[str, Any] = None,
        json: dict[str, Any] = None,
        timeout: float | None = None,
    ) -> requests.Response:
        response = self._session.put(
            f"{self._url}/{endpoint}", params=params, json=json, timeout=timeout
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
        response = self._session.post(
            f"{self._url}/{endpoint}", data=data, json=json, timeout=timeout
        )
        response.raise_for_status()
        return response

    def delete(
        self, endpoint: str, params: dict[str, Any] = None, timeout: float | None = None
    ) -> requests.Response:
        response = self._session.delete(
            f"{self._url}/{endpoint}", params=params, timeout=timeout
        )
        response.raise_for_status()
        return response

    def get_jobs(self) -> models.JobsResponse:
        endpoint = f"slurm/{self._version}/jobs"
        response = self.get(endpoint)
        return models.JobsResponse(**response.json())

    def get_job_info(self, job_id: int) -> models.JobsResponse:
        endpoint = f"slurm/{self._version}/job/{job_id}"
        response = self.get(endpoint)
        return models.JobsResponse(**response.json())

    def submit_job(
        self, job_submission: models.JobSubmission
    ) -> models.JobSubmissionResponse:
        endpoint = f"slurm/{self._version}/job/submit"
        response = self.post(endpoint, json=job_submission.dict(exclude_defaults=True))
        return models.JobSubmissionResponse(**response.json())
