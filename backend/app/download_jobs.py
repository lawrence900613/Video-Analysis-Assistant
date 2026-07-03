"""In-memory download jobs with yt-dlp progress tracking."""
from __future__ import annotations

import re
import shutil
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from yt_dlp.utils import DownloadCancelled

from . import downloader


@dataclass
class DownloadJob:
    job_id: str
    stage: str = "starting"
    percent: Optional[int] = None
    speed_bps: Optional[float] = None
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    filepath: Optional[Path] = None
    filename: Optional[str] = None
    job_dir: Optional[Path] = field(default=None, repr=False)
    _cancelled: bool = field(default=False, repr=False)
    _thread: Optional[threading.Thread] = field(default=None, repr=False)

    def snapshot(self) -> dict:
        out: dict = {
            "stage": self.stage,
            "percent": self.percent,
            "error": self.error,
            "ready": self.stage == "ready" and self.filepath is not None,
            "cancelled": self._cancelled or self.stage == "cancelled",
        }
        if self.speed_bps is not None:
            out["speed_bps"] = self.speed_bps
        if self.eta_seconds is not None:
            out["eta_seconds"] = self.eta_seconds
        if self.filename:
            out["filename"] = self.filename
        return out


_jobs: dict[str, DownloadJob] = {}
_lock = threading.Lock()


def _clean_err(e: Exception) -> str:
    msg = str(e)
    msg = re.sub(r"\x1b\[[0-9;]*m", "", msg)
    msg = re.sub(r"^ERROR:\s*", "", msg, flags=re.IGNORECASE).strip()
    return msg[:300] if msg else e.__class__.__name__


def _cleanup_job_dir(job: DownloadJob) -> None:
    if job.filepath and job.filepath.exists():
        try:
            job.filepath.unlink(missing_ok=True)
        except OSError:
            pass
    folder = job.job_dir or (job.filepath.parent if job.filepath else None)
    if folder and folder.exists():
        shutil.rmtree(folder, ignore_errors=True)
    job.filepath = None
    job.filename = None


def start_download(url: str, format_id: str) -> str:
    job_id = uuid.uuid4().hex
    job = DownloadJob(job_id=job_id)
    with _lock:
        _jobs[job_id] = job

    def _on_progress(
        stage: str,
        percent: Optional[int],
        speed_bps: Optional[float] = None,
        eta_seconds: Optional[int] = None,
    ) -> None:
        with _lock:
            if job._cancelled:
                return
            job.stage = stage
            job.percent = percent
            if stage == "processing":
                job.speed_bps = None
                job.eta_seconds = None
            else:
                job.speed_bps = speed_bps
                job.eta_seconds = eta_seconds

    def _should_cancel() -> bool:
        with _lock:
            return job._cancelled

    def _on_job_dir(path: Path) -> None:
        with _lock:
            job.job_dir = path

    def _run() -> None:
        try:
            filepath = downloader.download(
                url,
                format_id,
                on_progress=_on_progress,
                should_cancel=_should_cancel,
                on_job_dir=_on_job_dir,
            )
            with _lock:
                if job._cancelled:
                    _cleanup_job_dir(job)
                    job.stage = "cancelled"
                    return
                job.filepath = filepath
                job.filename = filepath.name
                job.job_dir = filepath.parent
                job.stage = "ready"
                job.percent = 100
        except DownloadCancelled:
            with _lock:
                job.stage = "cancelled"
                _cleanup_job_dir(job)
        except Exception as e:  # noqa: BLE001
            with _lock:
                if job._cancelled:
                    job.stage = "cancelled"
                    _cleanup_job_dir(job)
                else:
                    job.stage = "error"
                    job.error = _clean_err(e)

    thread = threading.Thread(target=_run, daemon=True)
    job._thread = thread
    thread.start()
    return job_id


def get_job(job_id: str) -> Optional[DownloadJob]:
    with _lock:
        return _jobs.get(job_id)


def take_job(job_id: str) -> Optional[DownloadJob]:
    with _lock:
        return _jobs.pop(job_id, None)


def cancel_job(job_id: str) -> dict:
    """Request cancellation. Returns status dict for the API response."""
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return {"status": "not_found"}
        if job._cancelled or job.stage == "cancelled":
            return {"status": "already_cancelled"}
        if job.stage == "ready":
            _cleanup_job_dir(job)
            job._cancelled = True
            job.stage = "cancelled"
            return {"status": "cancelled"}
        if job.stage == "error":
            return {"status": "already_finished", "stage": job.stage}

        job._cancelled = True
        job.stage = "cancelled"
        job.speed_bps = None
        job.eta_seconds = None
        _cleanup_job_dir(job)
        return {"status": "cancelled"}
