# Excel and PowerPoint canonical text (spec, written 9 Oct by Claude for Lina's approval)

*Owed since 2 Oct (LEDGER_SCHEMA §7, §12). Implements the 3 Oct Excel evidence decisions (DECISIONS.md, "Excel evidence (20 Oct adapter specification)"). Built the same day in `adapters.py`; not accepted until Lina reviews it. Nothing in the evaluated pipeline changes: adapters only produce text, which reaches extraction and the rules through the existing path.*

## Why a canonical text at all (UNDERSTAND)

Extraction, the quote checker and the rules all read **one plain text** per document version. A spreadsheet or a deck has no natural reading order, so the adapter fixes one, and records where every piece came from (`location_map`). The same file always gives the same text (same hash), so the extraction cache and freshness keep working.

## Excel (.xlsx)

- **Order:** every worksheet in workbook order, including hidden ones; rows top to bottom; cells left to right. Chart sheets are skipped (noted).
- **Sheet marker:** a line `[Sheet: <name>]`, or `[Sheet: <name> (hidden)]`, before the sheet's rows; a blank line between sheets.
- **One row per line, cells joined by ` | `** — the same shape the rules already read in Markdown and Word pricing notes (one table row per line, the approval in the last cell). Empty cells inside a row are kept as empty positions so columns stay aligned; trailing empty cells and empty rows are dropped.
- **Values, never formulas.** A formula cell counts by its **stored (cached) value** only. If there is no stored value, or it is an error (`#REF!`, `#N/A` …), the cell reads `[no stored value]` and the document gets a note. Never a guessed or recalculated value.
  - Gap to decide: the 3 Oct decision says such a cell gives *Needs evidence*. With rules unchanged, a pricing-note row whose approval cell reads `[no stored value]` matches neither approved nor not-approved and falls through to **No approval recorded** — conservative (never a false approval), but not *Needs evidence*. Making it *Needs evidence* is a `rules.py` change, which is in the evaluated pipeline; decide before the 12 Oct freeze.
- **Numbers:** whole numbers without decimals (`40000`, not `40000.0`); dates as `2026-10-14`; booleans `TRUE` / `FALSE`.
- **Hidden is read, flagged, and assessed like anything else** (3 Oct decision: hidden is a display setting, not a measure of authority). Hidden sheets, rows and columns are all read; `location_map` carries a `hidden` flag per row; the document gets one note per hidden sheet and a count of hidden rows/columns.
- **location_map:** one entry per row: `{"sheet", "row", "cells": "A5:D5", "hidden": "sheet" | "row" | "column" | null, "start", "end"}`. A quote traces back to sheet and row.
- **Refused:** `.xls` (old format), `.xlsm` (macros), password-protected files, more than 200,000 non-empty cells, over 50 MB unpacked.
- **Not read (noted):** comments, charts, images, pivot caches, external links.

## PowerPoint (.pptx)

- **Order:** slides in deck order; on each slide the title first, then other shapes in the order they are stored; groups are opened; tables one row per line with ` | `.
- **Slide marker:** `[Slide N]`, or `[Slide N (hidden)]` for a hidden slide, then its text; a blank line between slides.
- **Hidden slides are read and flagged** (proposed; Lina to decide). Reason to read: a hidden slide can still be sent or presented. Reason not to: it may never have reached the customer. The marker and a note make it visible either way.
- **Speaker notes are not read** (proposed; noted when present), the same choice as Word comments: they are the presenter's words to themselves, not what the customer saw.
- **location_map:** one entry per slide `{"slide", "hidden", "start", "end"}`.
- **Refused:** `.ppt` (old format), `.pptm` (macros), password-protected files, over 300 slides, over 50 MB unpacked.
- **Not read (noted):** images, charts, SmartArt, embedded objects, audio/video.

## What the screen shows

The document list shows the format (Excel / PowerPoint) and the notes. A quote from a spreadsheet shows its sheet and row ("Sheet Approvals, row 5"); from a deck, its slide ("slide 4").
