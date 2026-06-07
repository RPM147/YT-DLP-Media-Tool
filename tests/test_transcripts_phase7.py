from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from core.transcripts import (
    CookieLockedError,
    TranscriptCallbacks,
    TranscriptCancelledError,
    TranscriptProgress,
    TranscriptRequest,
    TranscriptService,
    UserError,
)
from transcript_worker import TranscriptWorker


def make_request(tmp_path: Path) -> TranscriptRequest:
    return TranscriptRequest(
        url="https://www.youtube.com/@phase7",
        output_dir=tmp_path,
        languages=("en",),
        delay=0,
    )


class SuccessService:
    def __init__(self) -> None:
        self.called = False

    def process(
        self,
        _request: TranscriptRequest,
        callbacks: TranscriptCallbacks,
    ) -> dict[str, Any]:
        self.called = True
        assert callbacks.should_cancel is not None
        assert callbacks.should_cancel() is False
        assert callbacks.on_progress is not None
        assert callbacks.on_log is not None
        callbacks.on_progress(
            TranscriptProgress(
                index=1,
                total=1,
                global_index=1,
                video_id="vid1",
                title="Video",
                action="saved",
                message="manual, en",
            )
        )
        callbacks.on_log("[1/1] #1 Video: manual, en")
        return {"processed_count": 1}


def connect_worker_signals(worker: TranscriptWorker) -> dict[str, list[Any]]:
    seen: dict[str, list[Any]] = {
        "progress": [],
        "log": [],
        "result": [],
        "error": [],
        "error_detail": [],
        "cancelled": [],
        "finished": [],
    }
    worker.signals.progress.connect(seen["progress"].append)
    worker.signals.log.connect(seen["log"].append)
    worker.signals.result.connect(seen["result"].append)
    worker.signals.error.connect(seen["error"].append)
    worker.signals.error_detail.connect(seen["error_detail"].append)
    worker.signals.cancelled.connect(seen["cancelled"].append)
    worker.signals.finished.connect(lambda: seen["finished"].append(True))
    return seen


def test_worker_emits_progress_log_result_and_finished(
    tmp_path: Path,
    qtbot: Any,
):
    service = SuccessService()
    worker = TranscriptWorker(make_request(tmp_path), service=service)
    seen = connect_worker_signals(worker)

    worker.run()

    assert service.called is True
    assert seen["progress"][0].video_id == "vid1"
    assert seen["log"] == ["[1/1] #1 Video: manual, en"]
    assert seen["result"] == [{"processed_count": 1}]
    assert seen["error"] == []
    assert seen["cancelled"] == []
    assert seen["finished"] == [True]


def test_worker_cancel_before_run_does_not_call_service(
    tmp_path: Path,
    qtbot: Any,
):
    service = SuccessService()
    worker = TranscriptWorker(make_request(tmp_path), service=service)
    seen = connect_worker_signals(worker)

    worker.cancel()
    worker.run()

    assert service.called is False
    assert seen["cancelled"] == ["Cancelled"]
    assert seen["result"] == []
    assert seen["error"] == []
    assert seen["finished"] == [True]


def test_worker_maps_service_cancellation_to_cancelled_signal(
    tmp_path: Path,
    qtbot: Any,
):
    class CancelDuringService:
        def __init__(self) -> None:
            self.worker: TranscriptWorker | None = None

        def process(
            self,
            _request: TranscriptRequest,
            callbacks: TranscriptCallbacks,
        ) -> dict[str, Any]:
            assert callbacks.should_cancel is not None
            assert callbacks.should_cancel() is False
            assert self.worker is not None
            self.worker.cancel()
            assert callbacks.should_cancel() is True
            raise TranscriptCancelledError()

    service = CancelDuringService()
    worker = TranscriptWorker(make_request(tmp_path), service=service)
    service.worker = worker
    seen = connect_worker_signals(worker)

    worker.run()

    assert seen["cancelled"] == ["Cancelled"]
    assert seen["result"] == []
    assert seen["error"] == []
    assert seen["finished"] == [True]


def test_worker_maps_expected_user_errors_without_traceback(
    tmp_path: Path,
    qtbot: Any,
):
    class ErrorService:
        def process(
            self,
            _request: TranscriptRequest,
            _callbacks: TranscriptCallbacks,
        ) -> dict[str, Any]:
            raise UserError("No videos found for the provided URL.")

    worker = TranscriptWorker(make_request(tmp_path), service=ErrorService())
    seen = connect_worker_signals(worker)

    worker.run()

    assert seen["error"] == ["No videos found for the provided URL."]
    assert seen["error_detail"] == []
    assert seen["finished"] == [True]


def test_worker_maps_cookie_lock_to_shared_error_code(
    tmp_path: Path,
    qtbot: Any,
):
    class CookieService:
        def process(
            self,
            _request: TranscriptRequest,
            _callbacks: TranscriptCallbacks,
        ) -> dict[str, Any]:
            raise CookieLockedError()

    worker = TranscriptWorker(make_request(tmp_path), service=CookieService())
    seen = connect_worker_signals(worker)

    worker.run()

    assert seen["error"] == ["COOKIE_DB_LOCKED"]
    assert seen["error_detail"] == []
    assert seen["finished"] == [True]


def test_worker_sends_unexpected_exception_to_detail_log_only(
    tmp_path: Path,
    qtbot: Any,
):
    class BoomService:
        def process(
            self,
            _request: TranscriptRequest,
            _callbacks: TranscriptCallbacks,
        ) -> dict[str, Any]:
            raise RuntimeError("internal yt-dlp state leaked")

    worker = TranscriptWorker(make_request(tmp_path), service=BoomService())
    seen = connect_worker_signals(worker)

    worker.run()

    assert seen["error"] == ["Beklenmeyen transcript hatasi"]
    assert "RuntimeError: internal yt-dlp state leaked" in seen["error_detail"][0]
    assert seen["finished"] == [True]


def test_service_cancellation_during_retry_delay_is_not_swallowed(tmp_path: Path):
    sleep_calls: list[float] = []
    attempts = 0

    def list_videos(_url: str) -> tuple[str, list[dict[str, Any]]]:
        return (
            "Phase 7 Channel",
            [
                {
                    "id": "vid1",
                    "title": "Video",
                    "url": "https://www.youtube.com/watch?v=vid1",
                }
            ],
        )

    def fetch_metadata(_url: str) -> dict[str, Any]:
        nonlocal attempts
        attempts += 1
        raise RuntimeError("temporary metadata failure")

    def should_cancel() -> bool:
        return bool(sleep_calls)

    service = TranscriptService(
        list_videos=list_videos,
        fetch_metadata=fetch_metadata,
        download_subtitle=lambda *_args: None,
        sleeper=sleep_calls.append,
    )

    with pytest.raises(TranscriptCancelledError):
        service.process(
            TranscriptRequest(
                url="https://www.youtube.com/@phase7",
                output_dir=tmp_path,
                languages=("en",),
                retries=2,
                retry_delay=0.2,
                delay=0,
            ),
            TranscriptCallbacks(should_cancel=should_cancel),
        )

    assert attempts == 1
    assert sleep_calls
