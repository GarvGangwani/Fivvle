"""Unit tests for functions/research_engine/main.py (ADR 0020 Cloud Function receiver).

Imports the handler from the function package path; mocks threading, pipeline,
and DB init — no real GCP or network.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest

# Stub functions_framework before loading the handler (decorator passthrough).
_ff = MagicMock()
_ff.http = lambda fn: fn
sys.modules.setdefault("functions_framework", _ff)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_CF_DIR = _BACKEND_ROOT.parent / "functions" / "research_engine"
if str(_CF_DIR) not in sys.path:
    sys.path.insert(0, str(_CF_DIR))

import main as cf_main  # noqa: E402


class _FakeRequest:
    def __init__(self, body: dict | None) -> None:
        self._body = body

    def get_json(self, silent: bool = True) -> dict | None:
        return self._body


@pytest.fixture(autouse=True)
def _reset_handler_state() -> None:
    cf_main._initialized = False
    yield
    cf_main._initialized = False


@pytest.fixture
def mock_thread() -> MagicMock:
    with patch.object(cf_main.threading, "Thread") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield mock_cls, instance


@pytest.fixture
def noop_init() -> MagicMock:
    with patch.object(cf_main, "init_engine") as mock_init:
        yield mock_init


def test_valid_experiment_id_returns_202_and_starts_thread(
    mock_thread: tuple[MagicMock, MagicMock],
    noop_init: MagicMock,
) -> None:
    experiment_id = uuid4()
    mock_cls, mock_instance = mock_thread

    result = cf_main.research_engine_handler(
        _FakeRequest({"experiment_id": str(experiment_id)})
    )

    assert result == ("", 202)
    mock_cls.assert_called_once()
    call = mock_cls.call_args
    assert call.kwargs["target"] is cf_main._run_pipeline_blocking
    assert call.kwargs["args"] == (experiment_id,)
    assert call.kwargs["daemon"] is False
    assert call.kwargs["name"] == f"pipeline-{experiment_id}"
    mock_instance.start.assert_called_once()


def test_missing_experiment_id_returns_400_no_thread(
    mock_thread: tuple[MagicMock, MagicMock],
    noop_init: MagicMock,
) -> None:
    mock_cls, _ = mock_thread
    result = cf_main.research_engine_handler(_FakeRequest({}))
    assert result == ("missing experiment_id", 400)
    mock_cls.assert_not_called()


def test_invalid_experiment_id_returns_400_no_thread(
    mock_thread: tuple[MagicMock, MagicMock],
    noop_init: MagicMock,
) -> None:
    mock_cls, _ = mock_thread
    result = cf_main.research_engine_handler(
        _FakeRequest({"experiment_id": "not-a-uuid"})
    )
    assert result == ("invalid experiment_id", 400)
    mock_cls.assert_not_called()


def test_init_engine_failure_returns_500_no_thread(
    mock_thread: tuple[MagicMock, MagicMock],
) -> None:
    mock_cls, _ = mock_thread
    with patch.object(cf_main, "init_engine", side_effect=RuntimeError("db down")):
        result = cf_main.research_engine_handler(
            _FakeRequest({"experiment_id": str(uuid4())})
        )
    assert result == ("init failed", 500)
    mock_cls.assert_not_called()


def test_ensure_initialized_calls_init_engine_once_across_two_requests(
    mock_thread: tuple[MagicMock, MagicMock],
) -> None:
    mock_cls, mock_instance = mock_thread
    experiment_id = uuid4()

    with patch.object(cf_main, "init_engine") as mock_init_engine:
        with patch.object(cf_main, "_run_pipeline_blocking"):
            cf_main.research_engine_handler(
                _FakeRequest({"experiment_id": str(experiment_id)})
            )
            cf_main.research_engine_handler(
                _FakeRequest({"experiment_id": str(uuid4())})
            )

    assert mock_init_engine.call_count == 1
    mock_init_engine.assert_called_once_with(cf_main.get_settings())
    assert mock_cls.call_count == 2
    assert mock_instance.start.call_count == 2
