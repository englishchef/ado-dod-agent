"""Tests that orchestration storage access stays behind the storage abstraction."""

from __future__ import annotations

import inspect

from backend.app.graphs import nodes


def test_orchestration_nodes_use_storage_factory_for_non_local_backend() -> None:
    source = inspect.getsource(nodes._storage_store)

    assert "get_storage_store" in source
    assert "CosmosArtifactStore" not in inspect.getsource(nodes)
