"""Artifact readers: parsed JSON files (outline/enriched/layout) and image listing.

These functions never mutate the filesystem — read-only access to session outputs.
"""
import json
from pathlib import Path
from typing import Dict, Any, List

from backend.services.session_io import session_dir


def list_step_artifacts(session_id: str) -> Dict[str, Any]:
    """Return parsed JSON for outline/enriched/layout when present."""
    out: Dict[str, Any] = {}
    sdir = session_dir(session_id)
    for key, fname in (
        ("outline", "outline.json"),
        ("enriched", "enriched.json"),
        ("layout", "layout.json"),
    ):
        p = sdir / fname
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    out[key] = json.load(f)
            except Exception:
                out[key] = None
        else:
            out[key] = None
    return out


def list_images(session_id: str) -> List[Dict[str, Any]]:
    """List images under <session_dir>/images/, plus placeholders for missing pages.

    Real files come first with `url` set. Pages declared in layout.json that
    don't have a corresponding file (engine failure, user deletion, etc.) are
    appended as placeholders with `url=None`, so the UI can show a "未生成"
    card with a "重新生成" button instead of silently showing fewer images.
    """
    sdir = session_dir(session_id)
    d = sdir / "images"
    out: List[Dict[str, Any]] = []

    # Collect expected pages + their descriptions from layout.json
    expected: Dict[int, str] = {}
    layout_path = sdir / "layout.json"
    if layout_path.exists():
        try:
            with open(layout_path, "r", encoding="utf-8") as f:
                layout = json.load(f)
            for slide in (layout or {}).get("slides", []) or []:
                page = slide.get("page_number")
                img = slide.get("image")
                if not page or not img:
                    continue
                parts = []
                if img.get("prompt"):
                    parts.append(img["prompt"])
                elif img.get("description"):
                    parts.append(img["description"])
                if img.get("chart_type"):
                    parts.append(f"[{img['chart_type']}]")
                expected[int(page)] = "\n".join(parts) if parts else None
        except Exception:
            pass

    # List actual files on disk
    present_pages: set = set()
    if d.exists():
        for p in sorted(d.iterdir()):
            if not p.is_file():
                continue
            if p.suffix.lower() not in {".png", ".svg", ".jpg", ".jpeg"}:
                continue
            stem = p.stem
            if stem.startswith("page_"):
                page_str = stem[len("page_"):]
                try:
                    page = int(page_str)
                except ValueError:
                    page = None
            else:
                page = None
            item = {
                "filename": p.name,
                "page": page,
                "ext": p.suffix.lstrip(".").lower(),
                "url": f"/static/output/{session_id}/images/{p.name}",
            }
            if page is not None and page in expected:
                item["description"] = expected[page]
                present_pages.add(page)
            out.append(item)

    # Append placeholders for expected pages without a file
    for page, desc in expected.items():
        if page in present_pages:
            continue
        out.append({
            "filename": None,
            "page": page,
            "ext": None,
            "url": None,
            "description": desc,
        })

    # Sort by page number (None last) for stable UI order
    out.sort(key=lambda x: (x["page"] is None, x["page"] or 0))
    return out
