"""/api/sessions/{id}/steps/* endpoints, job polling, and asset reads.

Long-running step jobs are dispatched via FastAPI's BackgroundTasks and wrapped
with `run_in_threadpool` so that pipeline functions can safely call
`asyncio.run` without conflicting with the request event loop.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from backend.core.jobs import job_manager
from backend.services import artifacts, pipeline_service, session_io

router = APIRouter()


def _run_job(job_id: str, session_id: str, step: str, fn, *args) -> None:
    job_manager.update(job_id, status="running", stage=f"开始执行 {step}", progress=0.0)
    try:
        result = fn(session_id, *args) if args else fn(session_id)
        job_manager.update(
            job_id,
            status="success",
            stage="完成",
            progress=1.0,
            result=result or {},
        )
    except Exception as e:
        job_manager.update(job_id, status="error", error=str(e), stage="失败")


def _require_session(session_id: str) -> None:
    if not session_io.get_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")


def _already_done(session_id: str, step: str) -> bool:
    """该步产物是否已存在（链式语义：前置缺失则不算完成）。

    不能只看文件是否存在：重置中途失败可能留下孤立产物（例如没有 images
    的 output.pptx）。若把它当作"已完成"，一键执行会静默跳过 PPT 步骤，
    结果 pptx 停留在旧内容上，与新生成的图片不一致。
    """
    data = session_io.get_session(session_id) or {}
    return bool(data.get(f"has_{step}", False))


# ----------------- step triggers -----------------

# step 名 → (前置产物文件 | None, 前置缺失提示, 已完成提示, pipeline 函数)
_STEPS = {
    "outline": (None, None, "大纲已生成，请先重置", pipeline_service.run_outline),
    "content": ("outline.json", "请先生成大纲", "内容已生成，请先重置", pipeline_service.run_content),
    "layout":  ("enriched.json", "请先生成内容", "布局已生成，请先重置", pipeline_service.run_layout),
    "images":  ("layout.json", "请先生成布局", "图片已生成，请先重置", pipeline_service.run_images),
    "ppt":     ("images", "请先生成图片", "PPT 已生成，请先重置", pipeline_service.run_ppt),
}


def _dispatch_step(step: str, session_id: str, background_tasks: BackgroundTasks) -> dict:
    prev_file, prev_detail, done_reason, fn = _STEPS[step]
    _require_session(session_id)
    if prev_file and not (session_io.session_dir(session_id) / prev_file).exists():
        raise HTTPException(status_code=400, detail=prev_detail)
    if _already_done(session_id, step):
        return {"skipped": True, "reason": done_reason}
    job = job_manager.create(session_id, step)
    background_tasks.add_task(
        run_in_threadpool,
        _run_job, job.job_id, session_id, step, fn,
    )
    return {"job_id": job.job_id}


@router.post("/{session_id}/steps/outline")
async def step_outline(session_id: str, background_tasks: BackgroundTasks):
    return _dispatch_step("outline", session_id, background_tasks)


@router.post("/{session_id}/steps/content")
async def step_content(session_id: str, background_tasks: BackgroundTasks):
    return _dispatch_step("content", session_id, background_tasks)


@router.post("/{session_id}/steps/layout")
async def step_layout(session_id: str, background_tasks: BackgroundTasks):
    return _dispatch_step("layout", session_id, background_tasks)


@router.post("/{session_id}/steps/images")
async def step_images(session_id: str, background_tasks: BackgroundTasks):
    return _dispatch_step("images", session_id, background_tasks)


@router.post("/{session_id}/steps/ppt")
async def step_ppt(session_id: str, background_tasks: BackgroundTasks):
    return _dispatch_step("ppt", session_id, background_tasks)


# ----------------- regenerate / delete image -----------------

@router.post("/{session_id}/images/{page_number}/regenerate")
async def regen_image(session_id: str, page_number: int, background_tasks: BackgroundTasks):
    _require_session(session_id)
    job = job_manager.create(session_id, "regenerate_image")
    background_tasks.add_task(
        run_in_threadpool,
        _run_job, job.job_id, session_id, "regenerate_image",
        pipeline_service.regenerate_image, page_number,
    )
    return {"job_id": job.job_id}


@router.delete("/{session_id}/images/{page_number}")
def delete_image(session_id: str, page_number: int):
    _require_session(session_id)
    return {"deleted": pipeline_service.delete_image(session_id, page_number)}


# ----------------- job polling -----------------

@router.get("/{session_id}/jobs/{job_id}")
def get_job(session_id: str, job_id: str):
    job = job_manager.get(job_id)
    if not job or job.session_id != session_id:
        raise HTTPException(status_code=404, detail="job not found")
    return job.to_dict()


# ----------------- artifact reads -----------------

def _artifact_or_404(session_id: str, key: str, detail: str) -> dict:
    arts = artifacts.list_step_artifacts(session_id)
    if arts.get(key) is None:
        raise HTTPException(status_code=404, detail=detail)
    return arts[key]


@router.get("/{session_id}/outline")
def get_outline(session_id: str):
    return _artifact_or_404(session_id, "outline", "outline not found")


@router.get("/{session_id}/content")
def get_content(session_id: str):
    return _artifact_or_404(session_id, "enriched", "content not found")


@router.get("/{session_id}/layout")
def get_layout(session_id: str):
    return _artifact_or_404(session_id, "layout", "layout not found")


@router.get("/{session_id}/images")
def list_images(session_id: str):
    _require_session(session_id)
    return artifacts.list_images(session_id)


@router.get("/{session_id}/ppt")
def get_ppt(session_id: str):
    p = session_io.session_dir(session_id) / "output.pptx"
    if not p.exists():
        raise HTTPException(status_code=404, detail="ppt not found")
    return FileResponse(
        str(p),
        filename="presentation.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
