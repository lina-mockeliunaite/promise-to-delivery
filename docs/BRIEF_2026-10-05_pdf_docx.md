# Brief: text-based PDF and DOCX adapters (planned Tue 13 Oct, built 5 Oct)

*Drafted by Claude (project) for Lina's approval. Claude Code: propose files, libraries and tests first; wait for go-ahead. One change set.*

## Boundaries
- Do not change the evaluated pipeline (`extract.py`, `schema.py`, `sales_filter.py`, `ledger_consolidate.py`, `terms.py`, `references.py`, `rules.py`, `agent.py`), its prompts or hashes. Adapters only produce text; extraction receives it through the existing `attempt_extraction(..., text=...)` path.
- Never read `data/coral_pay/`. Same deal allowlist, write guard, `{deal}`-only path parameter. Uploads stay JSON (file bytes base64-encoded in the body) so the existing preflight protection still applies; set a size limit (e.g. 10 MB) and refuse anything else with a plain message.
- No model calls in tests (fake client). One real development run is Lina's, with her key, about $0.02.

## What to build
1. **`adapters.py`**: one function per format returning a canonical text plus a list of problems.
   - PDF (text layer only): page text in order, with a "[Page N]" marker per page. If a page has no text layer, report "Page N has no readable text (scanned or image-only; OCR is not supported in this build)". If no page has text, refuse the document.
   - DOCX: paragraphs in order, headings kept as their text, tables flattened row by row (cells joined with " | " inside the canonical text only, never shown to users as a raw row), headers and footers ignored. Report anything skipped (images, embedded objects) as a count.
   - Markdown and text: unchanged behaviour.
   - Record the adapter name and version with each source version, so the extraction cache key changes if the adapter changes.
2. **Upload**: the document upload accepts .pdf and .docx alongside .md and .txt. The Documents table shows the original format ("PDF", "Word") and any problems in plain language. Pricing notes in PDF or DOCX count as approval evidence (decided 3 Oct).
3. **Quotes trace back**: quote checking runs against the canonical text, and citations show "page N" for PDFs.

## Development checks (separate from the sealed evaluation)
- New fixtures, development only: the Harbour Bank proposal (HB-04) rendered as a text PDF and as a DOCX, plus one image-only PDF. Generate them with a script in `tests/fixtures/` or `data/dev_formats/`; never touch `data/harbour_bank/docs/`.
- Tests: canonical text of the PDF and DOCX variants contains every sentence of HB-04; page markers present; image-only PDF refused with the plain message; partial scanned page reported; oversize and wrong-type uploads refused; seal tests extended to the new upload path.
- Lina's real-model check: extract the PDF and DOCX variants once each and compare statements with the Markdown HB-04 run (same firm statements, quotes valid). Record cost and result in DECISIONS.md.

## Decisions for Lina (defaults above)
1. Libraries: Claude Code proposes (e.g. `pypdf` and `python-docx`), pinned in requirements.txt, with reasons.
2. Scanned PDF: refuse the whole document if no text, warn per page if partial.
3. Not validated by the sealed run: say so in the README and in the Documents table hint ("PDF and Word support is checked on development documents only").
