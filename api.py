"""Read-only local API for the Harbour Bank scaffold (step two).

Run: uvicorn api:app --host 127.0.0.1 --port 8000

GET routes only. No model calls, no uploads, no route takes a file path. The UI deal check
(config.UI_DEALS) runs before any filesystem call; config.py reads happen at call time.
"""

import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

import config

DIST_DIR = config.ROOT / "frontend" / "dist"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# One body for every rejected deal, so the response never echoes or distinguishes the requested name.
NOT_FOUND = "Not found"


def require_ui_deal(deal: str) -> str:
    """Return the deal if the UI may show it, else 404. Exact match, before any filesystem call."""
    if deal not in config.UI_DEALS:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return deal


def source_eligibility(doc_type) -> str:
    if doc_type in config.EXTRACTABLE_DOC_TYPES:
        return "extracted"
    if doc_type in config.REFERENCE_ONLY_DOC_TYPES:
        return "reference_only"
    return "unclassified"


def load_json(path: Path, what: str):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HTTPException(status_code=500, detail=f"{what} unavailable") from None


def latest_result_path(deal: str):
    """Newest results/extract_{deal}_YYYYMMDDTHHMMSSZ.json by the timestamp in the name, or None.

    Files that do not match the pattern are ignored; modification time is not used.
    """
    results_dir = config.RESULTS_DIR
    if not results_dir.is_dir():
        return None
    pattern = re.compile(rf"extract_{re.escape(deal)}_(\d{{8}}T\d{{6}}Z)\.json")
    best = None
    for path in results_dir.iterdir():
        match = pattern.fullmatch(path.name)
        if match and path.is_file() and not path.is_symlink():
            if best is None or match.group(1) > best[0]:
                best = (match.group(1), path)
    return best[1] if best else None


def create_app(dist_dir: Path = DIST_DIR) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.router.redirect_slashes = False
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)

    @app.get("/api/deals")
    def list_deals():
        return {"deals": list(config.UI_DEALS)}

    @app.get("/api/deals/{deal}/sources")
    def list_sources(deal: str):
        require_ui_deal(deal)
        manifest = load_json(config.doc_path(deal, "manifest.json"), "Source list")
        entries = manifest.get("documents") if isinstance(manifest, dict) else None
        if not isinstance(entries, list):
            raise HTTPException(status_code=500, detail="Source list unavailable")
        sources = [
            {
                "source_id": e.get("source_id"),
                "file": e.get("file"),
                "doc_type": e.get("doc_type"),
                "date": e.get("date"),
                "eligibility": source_eligibility(e.get("doc_type")),
            }
            for e in entries
            if isinstance(e, dict)
        ]
        return {"deal": deal, "sources": sources}

    @app.get("/api/deals/{deal}/results/latest")
    def latest_results(deal: str):
        require_ui_deal(deal)
        path = latest_result_path(deal)
        if path is None:
            return {"intermediate": True, "deal": deal, "run": None, "documents": [], "statements": []}
        result = load_json(path, "Results")
        docs = result.get("documents") if isinstance(result, dict) else None
        if not isinstance(docs, list):
            raise HTTPException(status_code=500, detail="Results unavailable")
        documents, statements = [], []
        for doc in docs:
            if not isinstance(doc, dict):
                continue
            documents.append({"source_id": doc.get("source_id"), "status": doc.get("status")})
            for s in doc.get("statements") or []:
                if isinstance(s, dict):
                    statements.append(
                        {
                            "statement_id": s.get("statement_id"),
                            "source_id": s.get("source_id"),
                            "quote": s.get("quote"),
                            "language": s.get("language"),
                            "speaker": s.get("speaker"),
                        }
                    )
        return {
            "intermediate": True,
            "deal": deal,
            "run": {
                "timestamp_utc": result.get("timestamp_utc"),
                "model": result.get("model"),
                "status_counts": result.get("status_counts"),
            },
            "documents": documents,
            "statements": statements,
        }

    # Mounted last so the /api routes win. Only the built frontend is served; skipped if not built yet.
    if dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")
    return app


app = create_app()
