import os
import time
from pathlib import Path

from app.services.storage_cleanup import purge_stale_jobs


def test_purge_stale_jobs_removes_only_old_dirs(tmp_path: Path, monkeypatch):
    uploads = tmp_path / "uploads"
    outputs = tmp_path / "outputs"
    uploads.mkdir()
    outputs.mkdir()

    old_job = uploads / "old"
    old_job.mkdir()
    (old_job / "source.pdf").write_bytes(b"x")
    stale_time = time.time() - 1000
    os.utime(old_job, (stale_time, stale_time))

    fresh_job = uploads / "fresh"
    fresh_job.mkdir()

    monkeypatch.setattr("app.services.storage_cleanup.UPLOADS", uploads)
    monkeypatch.setattr("app.services.storage_cleanup.OUTPUTS", outputs)

    purge_stale_jobs(max_age_seconds=500)

    assert not old_job.exists()
    assert fresh_job.exists()


def test_purge_stale_jobs_handles_missing_dirs(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("app.services.storage_cleanup.UPLOADS", tmp_path / "missing-uploads")
    monkeypatch.setattr("app.services.storage_cleanup.OUTPUTS", tmp_path / "missing-outputs")

    purge_stale_jobs()
