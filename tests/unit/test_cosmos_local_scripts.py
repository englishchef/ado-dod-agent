"""Tests for local Cosmos helper scripts without requiring an emulator."""

from __future__ import annotations

from pytest import CaptureFixture, MonkeyPatch
from scripts import init_cosmos_local, smoke_cosmos_local


def test_init_cosmos_local_does_not_print_secret(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    secret = "local-secret-key"
    monkeypatch.setenv("COSMOS_LOCAL_KEY", secret)
    monkeypatch.setenv("DOD_STORAGE_BACKEND", "cosmos_local")

    class FakeStore:
        def __init__(self, *_: object, **__: object) -> None:
            pass

        def initialize(self) -> None:
            return None

    monkeypatch.setattr(init_cosmos_local, "CosmosLocalStore", FakeStore)

    assert init_cosmos_local.main() == 0
    output = capsys.readouterr().out
    assert "local Cosmos initialized" in output
    assert secret not in output


def test_smoke_cosmos_local_handles_missing_emulator(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    monkeypatch.setenv("COSMOS_LOCAL_KEY", "local-secret-key")
    monkeypatch.setenv("DOD_STORAGE_BACKEND", "cosmos_local")

    def fake_get_storage_store(_: object) -> object:
        raise ConnectionError("connection refused")

    monkeypatch.setattr(smoke_cosmos_local, "get_storage_store", fake_get_storage_store)

    assert smoke_cosmos_local.main() == 2
    output = capsys.readouterr().out
    assert "local Cosmos smoke test could not reach or use the emulator" in output
    assert "local-secret-key" not in output
