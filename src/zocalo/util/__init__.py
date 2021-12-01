from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, Optional

import zocalo


def extended_status_dictionary() -> Dict[str, str]:
    """Returns a dictionary of extra fields that can be appended to log
    messages to provide further relevant contextual information."""
    extended_status = {"zocalo": zocalo.__version__}

    if os.getenv("JOB_ID"):
        # Instance may be running as an SGE cluster job
        extended_status["cluster_JOB_ID"] = os.environ["JOB_ID"]
        if os.getenv("SGE_CELL"):
            extended_status["cluster_SGE_CELL"] = os.environ["SGE_CELL"]
        sge_config = os.getenv("SGE_JOB_SPOOL_DIR")
        if sge_config:
            # This may not be trustworthy, so try to verify against the
            # job configuration. Don't worry if this doesn't work.
            try:
                sge_data = Path(sge_config, "config").read_text()
                for line in sge_data.split("\n"):
                    if line.upper().startswith("SGE_CELL="):
                        extended_status["cluster_SGE_CELL"] = line[9:]
                        break
            except Exception:
                pass

    k8s = get_kubernetes_pod_information()
    if k8s:
        if k8s.get("image"):
            extended_status["container_image"] = k8s["image"]
        extended_status["container_node"] = k8s["node"]

    return extended_status


def get_kubernetes_pod_information() -> Optional[Dict[str, str]]:
    """Detects if instance is running inside a Kubernetes pod, and, if so,
    obtains pod information via the Kubernetes API."""

    serviceaccount = Path("/var/run/secrets/kubernetes.io/serviceaccount")
    cacert = serviceaccount / "ca.crt"
    if not serviceaccount.is_dir() or not cacert.is_file():
        return None
    try:
        namespace = serviceaccount.joinpath("namespace").read_text()
        token = serviceaccount.joinpath("token").read_text()
    except Exception:
        return None
    hostname = os.getenv("HOSTNAME")

    query = subprocess.run(
        (
            "curl",
            "-fs",
            "--cacert",
            cacert,
            "--header",
            f"Authorization: Bearer {token}",
            "-X",
            "GET",
            f"https://kubernetes.default.svc/api/v1/namespaces/{namespace}/pods/{hostname}",
        ),
        capture_output=True,
    )
    if query.returncode or query.stderr:
        return None
    try:
        k8s = json.loads(query.stdout)
    except Exception:
        return None

    k8s_information = {}

    images = {c.get("image") for c in k8s["spec"]["containers"]}
    k8s_information["image"] = ",".join(i for i in images if i)
    k8s_information["node"] = k8s["spec"]["nodeName"]

    return k8s_information
