"""Tests for official Cosmos helper scripts without requiring an emulator."""

from __future__ import annotations

from pytest import CaptureFixture, MonkeyPatch
from scripts import init_cosmos, smoke_cosmos


def test_init_cosmos_does_not_print_secret(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    secret = "local-secret-key"
    monkeypatch.setenv("COSMOS_KEY", secret)
    monkeypatch.setenv("COSMOS_ENDPOINT", "https://localhost:8081")
    monkeypatch.setenv("COSMOS_DATABASE", "dod_agent_local")
    monkeypatch.setenv("COSMOS_CONTAINER", "dod_runs")
    monkeypatch.setenv("COSMOS_AUTH_MODE", "emulator_key")

    class FakeStore:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def initialize(self) -> None:
            return None

    monkeypatch.setattr(init_cosmos, "CosmosArtifactStore", FakeStore)

    assert init_cosmos.main([]) == 0
    output = capsys.readouterr().out
    assert "Cosmos artifact store initialized" in output
    assert secret not in output


def test_smoke_cosmos_handles_missing_emulator(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    monkeypatch.setenv("COSMOS_KEY", "local-secret-key")
    monkeypatch.setenv("COSMOS_ENDPOINT", "https://localhost:8081")
    monkeypatch.setenv("COSMOS_DATABASE", "dod_agent_local")
    monkeypatch.setenv("COSMOS_CONTAINER", "dod_runs")
    monkeypatch.setenv("COSMOS_AUTH_MODE", "emulator_key")

    def fake_get_storage_store(*_: object, **__: object) -> object:
        raise ConnectionError("connection refused")

    monkeypatch.setattr(smoke_cosmos, "get_storage_store", fake_get_storage_store)

    assert smoke_cosmos.main([]) == 2
    output = capsys.readouterr().out
    assert "Cosmos smoke test failed" in output
    assert "local-secret-key" not in output
