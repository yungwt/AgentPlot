"""/api/sessions endpoints (CRUD + reset)."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.services import session_io
from backend.core.config import MIN_PAGE_COUNT, MAX_PAGE_COUNT

router = APIRouter()


class CreateSessionReq(BaseModel):
    user_request: str = Field(..., min_length=1, max_length=2000)
    page_count: int = Field(3, ge=MIN_PAGE_COUNT, le=MAX_PAGE_COUNT)


@router.post("")
def create_session(req: CreateSessionReq):
    return session_io.create_session(req.user_request, req.page_count)


@router.get("")
def list_sessions():
    return session_io.list_sessions()


@router.get("/{session_id}")
def get_session(session_id: str):
    data = session_io.get_session(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="session not found")
    return data


@router.delete("/{session_id}")
def delete_session(session_id: str):
    ok = session_io.delete_session(session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="session not found")
    return {"deleted": True}


@router.post("/{session_id}/reset")
def reset_session(session_id: str, target_step: int = Query(..., ge=0, le=5)):
    if not session_io.get_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    session_io.reset_to_step(session_id, target_step)
    return session_io.get_session(session_id)
