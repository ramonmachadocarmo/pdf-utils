import shutil
import time

from app.config import JOB_TTL_SECONDS, OUTPUTS, UPLOADS


def purge_stale_jobs(max_age_seconds: float = JOB_TTL_SECONDS) -> None:
    cutoff = time.time() - max_age_seconds
    for root in (UPLOADS, OUTPUTS):
        if not root.exists():
            continue
        for job_dir in root.iterdir():
            if not job_dir.is_dir():
                continue
            if job_dir.stat().st_mtime < cutoff:
                shutil.rmtree(job_dir, ignore_errors=True)
