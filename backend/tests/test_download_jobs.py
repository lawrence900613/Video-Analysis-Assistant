"""Unit tests for download job cancellation (no network)."""
from yt_dlp.utils import DownloadCancelled

from app import download_jobs


def test_cancel_job_not_found():
    assert download_jobs.cancel_job("missing") == {"status": "not_found"}


def test_cancel_job_marks_cancelling():
    job_id = "test-job-id"
    job = download_jobs.DownloadJob(job_id=job_id, stage="downloading", percent=42)
    download_jobs._jobs[job_id] = job

    result = download_jobs.cancel_job(job_id)

    assert result == {"status": "cancelling"}
    assert job._cancelled is True
    assert job.stage == "cancelling"
    assert job.speed_bps is None

    download_jobs._jobs.pop(job_id, None)


def test_cancel_ready_job_cleans_up(tmp_path):
    job_id = "ready-job"
    filepath = tmp_path / "video.mp4"
    filepath.write_bytes(b"data")
    job = download_jobs.DownloadJob(
        job_id=job_id,
        stage="ready",
        filepath=filepath,
        filename="video.mp4",
        job_dir=tmp_path,
    )
    download_jobs._jobs[job_id] = job

    result = download_jobs.cancel_job(job_id)

    assert result == {"status": "cancelled"}
    assert job.stage == "cancelled"
    assert job.filepath is None
    assert not filepath.exists()

    download_jobs._jobs.pop(job_id, None)


def test_cancel_already_cancelled():
    job_id = "cancelled-job"
    job = download_jobs.DownloadJob(job_id=job_id, stage="cancelled")
    download_jobs._jobs[job_id] = job

    assert download_jobs.cancel_job(job_id) == {"status": "already_cancelled"}

    download_jobs._jobs.pop(job_id, None)


def test_start_download_handles_cancelled(monkeypatch):
    def fake_download(url, format_id, on_progress=None, should_cancel=None):
        if should_cancel:
            should_cancel()
        raise DownloadCancelled("Download cancelled by user")

    monkeypatch.setattr(download_jobs.downloader, "download", fake_download)
    job_id = download_jobs.start_download("http://example.com", "best")

    import time

    for _ in range(50):
        job = download_jobs.get_job(job_id)
        if job and job.stage == "cancelled":
            break
        time.sleep(0.05)

    job = download_jobs.get_job(job_id)
    assert job is not None
    assert job.stage == "cancelled"
    assert job.snapshot()["cancelled"] is True

    download_jobs._jobs.pop(job_id, None)
