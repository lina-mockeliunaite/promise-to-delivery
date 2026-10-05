"""Local API for the deal workspace. Bound to 127.0.0.1; no public model-backed endpoint.

Run: uvicorn api:app --host 127.0.0.1 --port 8000

Handoff routes (5 Oct) save and export an immutable snapshot of a review; the saved version travels as ?version=N.
Step two (read-only) routes are unchanged. The workspace routes (13 Oct block, built 3 Oct) read and write the ledger:
documents (text/Markdown upload, include/exclude), Review deal, the register, fixes and issue owner/notes. Rules:
- No route takes a file path; the only path parameter is {deal}. Everything else travels in a JSON body.
- A deal is either in config.UI_DEALS or a user deal (u_ + 16 hex) that exists in the ledger; anything else is one
  generic 404, checked before any database or filesystem access. Coral Pay is never in either.
- Writes need a JSON body and the header X-Requested-With: deal-workspace, which forces a CORS preflight that this
  server never grants, so another website in the same browser cannot post to it.
- A review that needs new extraction uses the API key from the server's environment only; the browser never sees it.
"""

import json
import re
from pathlib import Path

import os
import sqlite3

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

import config
import extraction_cache
import handoff
import ledger
import ledger_fixes
import recheck
import workspace

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


def create_app(dist_dir: Path = DIST_DIR, ledger_path=None) -> FastAPI:
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

    # --- Workspace (ledger-backed) -------------------------------------------------------------------------
    def db():
        path = ledger_path if ledger_path is not None else config.LEDGER_DB_PATH
        if not Path(path).exists():
            raise HTTPException(status_code=503, detail="The workspace database is not built yet.")
        conn = ledger.connect(path, check_same_thread=False)
        try:
            yield conn
        finally:
            conn.close()

    def workspace_deal(deal: str, conn) -> str:
        if deal in config.UI_DEALS:
            if conn.execute("SELECT 1 FROM deals WHERE slug = ? AND kind = 'development'", (deal,)).fetchone():
                return deal
        elif ledger_fixes.USER_SLUG.fullmatch(deal or ""):
            if conn.execute("SELECT 1 FROM deals WHERE slug = ? AND kind = 'user'", (deal,)).fetchone():
                return deal
        raise HTTPException(status_code=404, detail=NOT_FOUND)

    def write_guard(x_requested_with: str | None = Header(default=None), content_type: str | None = Header(default=None)):
        if x_requested_with != "deal-workspace" or not (content_type or "").startswith("application/json"):
            raise HTTPException(status_code=403, detail="Forbidden")

    def bad_request(exc):
        return HTTPException(status_code=400, detail=str(exc))

    def model_client():
        if not os.environ.get("ANTHROPIC_API_KEY"):  # presence only; the value is never read here or returned
            return None
        import anthropic
        return anthropic.Anthropic()

    @app.get("/api/workspace/deals")
    def ws_deals(conn=Depends(db)):
        return {"deals": workspace.deal_list(conn)}

    @app.post("/api/user-deals", dependencies=[Depends(write_guard)])
    def ws_create_deal(body: dict = Body(...), conn=Depends(db)):
        try:
            return {"deal": ledger_fixes.create_user_deal(conn, str(body.get("name", "")))}
        except ledger_fixes.FixError as exc:
            raise bad_request(exc) from None

    @app.get("/api/deals/{deal}/documents")
    def ws_documents(deal: str, conn=Depends(db)):
        workspace_deal(deal, conn)
        return {"deal": deal, "documents": workspace.documents(conn, deal),
                "doc_types": [{"value": k, "label": v} for k, v in workspace.DOC_TYPE_LABELS.items()]}

    @app.post("/api/deals/{deal}/documents", dependencies=[Depends(write_guard)])
    def ws_add_document(deal: str, body: dict = Body(...), conn=Depends(db)):
        workspace_deal(deal, conn)
        text = body.get("text")
        if not isinstance(text, str) or len(text.encode("utf-8")) > 1_000_000:
            raise HTTPException(status_code=400, detail="Send the document as text, up to 1 MB.")
        try:
            if body.get("source_key"):
                vid = ledger_fixes.add_source_version(conn, deal, str(body["source_key"]), text,
                                                      str(body.get("filename") or "upload.md")[:200],
                                                      body.get("doc_type") or None, body.get("doc_date") or None)
            else:
                vid = ledger_fixes.add_source(conn, deal, str(body.get("name") or ""), text,
                                              str(body.get("filename") or "upload.md")[:200],
                                              str(body.get("doc_type") or ""), str(body.get("doc_date") or ""))
        except ledger_fixes.FixError as exc:
            raise bad_request(exc) from None
        return {"source_version_id": vid}

    @app.post("/api/deals/{deal}/documents/include", dependencies=[Depends(write_guard)])
    def ws_include(deal: str, body: dict = Body(...), conn=Depends(db)):
        workspace_deal(deal, conn)
        try:
            ledger_fixes.set_included(conn, deal, str(body.get("source_key", "")), bool(body.get("included")))
        except ledger_fixes.FixError as exc:
            raise bad_request(exc) from None
        return {"ok": True}

    @app.post("/api/deals/{deal}/review", dependencies=[Depends(write_guard)])
    def ws_review(deal: str, body: dict = Body(default={}), conn=Depends(db)):
        workspace_deal(deal, conn)
        fix_id = body.get("fix_id")
        try:
            result = recheck.recheck(conn, deal, int(fix_id) if fix_id is not None else None, model_client())
        except extraction_cache.ExtractionFailed:
            raise HTTPException(status_code=409, detail=(
                "This review needs the model to read new or changed documents. Restart the server with the API key "
                "set in its terminal, then review again.")) from None
        except (recheck.RecheckError, ledger_fixes.FixError) as exc:
            raise bad_request(exc) from None
        return {"review": {k: result[k] for k in ("run_kind", "model_calls", "cost_usd", "checks")}}

    @app.get("/api/deals/{deal}/register")
    def ws_register(deal: str, conn=Depends(db)):
        workspace_deal(deal, conn)
        return workspace.register(conn, deal)

    @app.post("/api/deals/{deal}/fixes", dependencies=[Depends(write_guard)])
    def ws_fix(deal: str, body: dict = Body(...), conn=Depends(db)):
        workspace_deal(deal, conn)
        try:
            evidence = [(int(e["source_version_id"]), str(e.get("locator") or "whole document")[:200], None)
                        for e in body.get("evidence") or []]
            # One transaction: the draft and its sign-off are saved together or not at all, so a refused sign-off
            # never leaves an unapproved draft behind.
            fix_id = ledger_fixes.create_fix(conn, deal, str(body.get("route", "")), str(body.get("owner", "")),
                                             str(body.get("rationale", "")), [int(i) for i in body.get("issue_ids") or []],
                                             evidence, commit=False)
            ledger_fixes.approve_fix(conn, fix_id, str(body.get("approved_by", "")), commit=False)
            conn.commit()
        except (ledger_fixes.FixError, KeyError, ValueError, TypeError) as exc:
            conn.rollback()
            raise bad_request(exc) from None
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise HTTPException(status_code=400, detail=f"Refused by the ledger: {exc}") from None
        return {"fix_id": fix_id}

    @app.post("/api/deals/{deal}/issues", dependencies=[Depends(write_guard)])
    def ws_issue(deal: str, body: dict = Body(...), conn=Depends(db)):
        """Owner and note only. Neither marks the review out of date; neither can change an issue's state."""
        workspace_deal(deal, conn)
        did = ledger_fixes.deal_id(conn, deal)
        iid = body.get("issue_id")
        if not conn.execute("SELECT 1 FROM issues i JOIN commitments c ON c.id = i.commitment_id WHERE i.id = ?"
                            " AND c.deal_id = ?", (iid, did)).fetchone():
            raise HTTPException(status_code=404, detail=NOT_FOUND)
        try:
            if "owner" in body:
                conn.execute("UPDATE issues SET owner_function = ? WHERE id = ?", (str(body["owner"]), iid))
            if "note" in body:
                conn.execute("UPDATE issues SET note = ? WHERE id = ?", (str(body["note"])[:2000], iid))
            conn.commit()
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status_code=400, detail=f"Refused by the ledger: {exc}") from None
        return {"ok": True}

    # --- Handoff (saved snapshots and exports) --------------------------------------------------------------
    def saved_version(deal: str, version, conn):
        found = handoff.get_version(conn, deal, version)
        if found is None:
            raise HTTPException(status_code=404, detail=NOT_FOUND)
        return found

    @app.post("/api/deals/{deal}/handoffs", dependencies=[Depends(write_guard)])
    def ws_handoff_save(deal: str, body: dict = Body(...), conn=Depends(db)):
        workspace_deal(deal, conn)
        review_id = body.get("review_id")
        try:
            saved = handoff.save(conn, deal, body.get("decision"), body.get("reviewer"), body.get("note"),
                                 body.get("confirmed_issue_ids") or [], int(review_id) if review_id is not None else None)
        except handoff.HandoffError as exc:
            raise HTTPException(status_code=exc.status, detail=str(exc)) from None
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="The request was not understood.") from None
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="Another handoff was saved at the same time. Try again.") from None
        return saved

    @app.get("/api/deals/{deal}/handoffs")
    def ws_handoff_list(deal: str, conn=Depends(db)):
        workspace_deal(deal, conn)
        return {"versions": handoff.list_versions(conn, deal)}

    @app.get("/api/deals/{deal}/handoffs/view")
    def ws_handoff_view(deal: str, version: int | None = Query(default=None), conn=Depends(db)):
        workspace_deal(deal, conn)
        return saved_version(deal, version, conn)

    @app.get("/api/deals/{deal}/handoffs/export.csv")
    def ws_handoff_csv(deal: str, version: int | None = Query(default=None), conn=Depends(db)):
        workspace_deal(deal, conn)
        found = saved_version(deal, version, conn)
        name = handoff.export_filename(found["handoff"], found["version"], "csv")
        return Response(handoff.render_csv(found["handoff"]), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{name}"', "X-Content-Type-Options": "nosniff"})

    @app.get("/api/deals/{deal}/handoffs/summary")
    def ws_handoff_summary(deal: str, version: int | None = Query(default=None), conn=Depends(db)):
        workspace_deal(deal, conn)
        found = saved_version(deal, version, conn)
        return Response(handoff.render_html(found["handoff"], found["version"]), media_type="text/html; charset=utf-8",
                        headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
                                 "X-Content-Type-Options": "nosniff"})

    # Mounted last so the /api routes win. Only the built frontend is served; skipped if not built yet.
    if dist_dir.is_dir():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")
    return app


app = create_app()
