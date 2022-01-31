from __future__ import annotations

import zocalo.util


def test_can_extract_kubernetes_information():
    kubernetes = zocalo.util.get_kubernetes_pod_information()

    if kubernetes is None:
        return
    assert kubernetes["node"]


def test_extended_status():
    status = zocalo.util.extended_status_dictionary()

    assert status["zocalo"] == zocalo.__version__
