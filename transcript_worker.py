"""Qt worker wrapper for transcript archiving jobs."""

from __future__ import annotations

import threading
import traceback
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from core.transcripts.models import (
    CookieLockedError,
    TranscriptCallbacks,
    TranscriptCancelledError,
    TranscriptRequest,
    UserError,
)
from core.transcripts.service import TranscriptService


class TranscriptWorkerSignals(QObject):
    """Signals emitted by TranscriptWorker."""

    progress = pyqtSignal(object)
    log = pyqtSignal(str)
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    error_detail = pyqtSignal(str)
    cancelled = pyqtSignal(str)
    finished = pyqtSignal()


class TranscriptWorker(QRunnable):
    """Run TranscriptService on a thread-pool worker with cancellation support."""

    def __init__(
        self,
        request: TranscriptRequest,
        *,
        service: Any | None = None,
        cookie_browser: str | None = None,
        cookie_browser_profile: str | None = None,
        cookie_file: str | Path | None = None,
        ytdlp_module: Any | None = None,
    ) -> None:
        super().__init__()
        self.request = request
        self.signals = TranscriptWorkerSignals()
        self._cancel_event = threading.Event()
        self._service = service or TranscriptService(
            cookie_browser=cookie_browser,
            cookie_browser_profile=cookie_browser_profile,
            cookie_file=cookie_file,
            ytdlp_module=ytdlp_module,
        )

    def cancel(self) -> None:
        self._cancel_event.set()

    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def run(self) -> None:
        try:
            if self.is_cancelled():
                self.signals.cancelled.emit("Cancelled")
                return

            callbacks = TranscriptCallbacks(
                on_progress=self.signals.progress.emit,
                on_log=self.signals.log.emit,
                should_cancel=self.is_cancelled,
            )
            report = self._service.process(self.request, callbacks)
            self.signals.result.emit(report)
        except TranscriptCancelledError:
            self.signals.cancelled.emit("Cancelled")
        except CookieLockedError:
            self.signals.error.emit("COOKIE_DB_LOCKED")
        except UserError as exc:
            self.signals.error.emit(str(exc))
        except Exception:
            self.signals.error_detail.emit(traceback.format_exc())
            self.signals.error.emit("Beklenmeyen transcript hatasi")
        finally:
            self.signals.finished.emit()
