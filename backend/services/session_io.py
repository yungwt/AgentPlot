"""Session IO: CRUD + reset + history listing.

Pure read/write/listing operations on the OUTPUT_DIR. No artifact content parsing.
"""
import json
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.core.settings import OUTPUT_DIR


# ---------- constants ----------

STEP_NONE = 0
STEP_OUTLINE = 1
STEP_CONTENT = 2
STEP_LAYOUT = 3
STEP_IMAGES = 4
STEP_PPT = 5

STEP_LABELS = {
    STEP_NONE: "未开始",
    STEP_OUTLINE: "大纲",
    STEP_CONTENT: "内容",
    STEP_LAYOUT: "布局",
    STEP_IMAGES: "图片",
    STEP_PPT: "完成",
}

STEP_FILES = {
    STEP_OUTLINE: "outline.json",
    STEP_CONTENT: "enriched.json",
    STEP_LAYOUT: "layout.json",
    STEP_IMAGES: "images",
    STEP_PPT: "output.pptx",
}


# ---------- path helpers ----------

def session_dir(session_id: str) -> Path:
    return Path(OUTPUT_DIR) / session_id


def _has_file(session_id: str, name: str) -> bool:
    return (session_dir(session_id) / name).exists()


def _has_images(session_id: str) -> bool:
    d = session_dir(session_id) / "images"
    if not d.exists() or not d.is_dir():
        return False
    return any(
        p.suffix.lower() in {".png", ".svg", ".jpg", ".jpeg"}
        for p in d.iterdir()
        if p.is_file()
    )


def step_flags(session_id: str) -> Dict[str, bool]:
    """每一步「是否真正完成」—— 按链式（顺序依赖）语义判断。

    产物链是严格顺序的：outline → enriched → layout → images → pptx。
    只按「文件是否存在」判断会让孤立产物被误认为已完成，典型场景是重置
    中途失败后残留的 output.pptx：文件在，但 content/layout/images 都没了。

    因此某一步算完成的前提是 **它自己 + 它的全部前置产物都存在**。
    """
    has_outline = _has_file(session_id, "outline.json")
    has_content = has_outline and _has_file(session_id, "enriched.json")
    has_layout = has_content and _has_file(session_id, "layout.json")
    has_images = has_layout and _has_images(session_id)
    has_ppt = has_images and _has_file(session_id, "output.pptx")
    return {
        "has_outline": has_outline,
        "has_content": has_content,
        "has_layout": has_layout,
        "has_images": has_images,
        "has_ppt": has_ppt,
    }


_STEP_ORDER = (
    (STEP_OUTLINE, "has_outline"),
    (STEP_CONTENT, "has_content"),
    (STEP_LAYOUT, "has_layout"),
    (STEP_IMAGES, "has_images"),
    (STEP_PPT, "has_ppt"),
)


def _step_from_flags(flags: Dict[str, bool]) -> int:
    """连续进度 0..5：遇到第一个未完成的步骤就停（5 = 全部完成）。"""
    cs = STEP_NONE
    for step, key in _STEP_ORDER:
        if not flags.get(key):
            break
        cs = step
    return cs


def current_step(session_id: str) -> int:
    """0..5; 5 means fully done."""
    return _step_from_flags(step_flags(session_id))


# ---------- CRUD ----------

def create_session(user_request: str, page_count: int) -> Dict[str, Any]:
    sid = f"session_{int(time.time())}"
    sdir = session_dir(sid)
    sdir.mkdir(parents=True, exist_ok=True)
    config = {
        "user_request": user_request,
        "page_count": page_count,
        "created_at": time.time(),
    }
    with open(sdir / "config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return {
        "session_id": sid,
        "output_dir": str(sdir),
        "config": config,
        "current_step": STEP_NONE,
    }


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    sdir = session_dir(session_id)
    cfg_path = sdir / "config.json"
    if not cfg_path.exists():
        return None
    with open(cfg_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    flags = step_flags(session_id)
    cs = _step_from_flags(flags)
    return {
        "session_id": session_id,
        "output_dir": str(sdir),
        "config": config,
        "current_step": cs,
        "current_step_label": STEP_LABELS.get(cs, "未知"),
        **flags,
    }


def delete_session(session_id: str) -> bool:
    sdir = session_dir(session_id)
    if not sdir.exists():
        return False
    shutil.rmtree(sdir)
    return True


def reset_to_step(session_id: str, target_step: int) -> None:
    """Delete artifacts strictly AFTER target_step (idempotent).

    Semantics (N = target_step):
      0 (STEP_NONE)   → delete all artifacts (full reset, keeps config.json)
      1 (STEP_OUTLINE)→ keep outline.json, delete enriched+layout+images+pptx
      2 (STEP_CONTENT)→ keep outline+enriched, delete layout+images+pptx
      3 (STEP_LAYOUT) → keep outline+enriched+layout, delete images+pptx
      4 (STEP_IMAGES) → keep outline+enriched+layout+images, delete pptx only
      5 (STEP_PPT)    → no-op (everything already complete)

    In short: target_step = "rollback so that steps 1..N remain, N+1..5 are gone."
    """
    sdir = session_dir(session_id)
    if not sdir.exists():
        return
    for step in range(target_step + 1, STEP_PPT + 1):
        name = STEP_FILES.get(step)
        if not name:
            continue
        p = sdir / name
        if p.exists():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()


# ---------- history ----------

def list_sessions() -> List[Dict[str, Any]]:
    """List all session directories under OUTPUT_DIR with summary info.

    Sorted by created_at descending (newest first). Skips any dir that does not
    contain a readable config.json (e.g. partial / corrupted sessions).
    """
    out: List[Dict[str, Any]] = []
    if not Path(OUTPUT_DIR).exists():
        return out
    for sdir in Path(OUTPUT_DIR).iterdir():
        if not sdir.is_dir() or not sdir.name.startswith("session_"):
            continue
        cfg_path = sdir / "config.json"
        if not cfg_path.exists():
            continue
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            continue
        sid = sdir.name
        cs = current_step(sid)
        out.append({
            "session_id": sid,
            "user_request": cfg.get("user_request", "")[:60],
            "page_count": cfg.get("page_count", 0),
            "current_step": cs,
            "current_step_label": STEP_LABELS.get(cs, "未知"),
            "created_at": cfg.get("created_at", 0),
        })
    out.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return out
