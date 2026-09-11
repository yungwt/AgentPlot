"""In-memory job state manager for long-running pipeline steps."""
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class JobInfo:
    job_id: str
    session_id: str
    step: str                       # outline | content | layout | images | ppt | regenerate_image
    status: str = "pending"         # pending | running | success | error
    stage: str = ""                 # human-readable sub-stage
    progress: float = 0.0           # 0.0 - 1.0
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class JobManager:
    """Thread-safe in-memory job state."""

    def __init__(self) -> None:
        self._jobs: Dict[str, JobInfo] = {}
        self._lock = threading.Lock()

    def create(self, session_id: str, step: str) -> JobInfo:
        job = JobInfo(
            job_id=uuid.uuid4().hex[:12],
            session_id=session_id,
            step=step,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def update(
        self,
        job_id: str,
        *,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        progress: Optional[float] = None,
        error: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            if status is not None:
                job.status = status
            if stage is not None:
                job.stage = stage
            if progress is not None:
                job.progress = max(0.0, min(1.0, progress))
            if error is not None:
                job.error = error
            if result is not None:
                job.result = result
            job.updated_at = time.time()

    def get(self, job_id: str) -> Optional[JobInfo]:
        with self._lock:
            return self._jobs.get(job_id)


job_manager = JobManager()
