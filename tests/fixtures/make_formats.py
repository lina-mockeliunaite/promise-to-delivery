"""Development-only fixtures for the PDF and DOCX adapters, generated on demand; nothing binary is committed.

The source is the Harbour Bank proposal (HB-04), read-only through config.doc_path; nothing under data/ is written.
The PDF writer is hand-written (no PDF library): a text page is Helvetica lines, an image-only page draws a small
inline image and carries no text layer.

    python tests/fixtures/make_formats.py OUT_DIR     # writes hb04.pdf, hb04.docx, image_only.pdf, partial_scan.pdf
"""

import io
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import config

LINE_WIDTH = 88          # characters per line at 10.5pt Helvetica on a letter page, near enough for fixtures
LINES_PER_PAGE = 44


def hb04_markdown() -> str:
    return config.doc_path("harbour_bank", "HB-04_proposal.md").read_text(encoding="utf-8")


def hb04_blocks() -> list:
    """[(kind, text)] with kind 'heading' or 'para', in order. Markdown marks are removed, nothing else changes."""
    blocks = []
    for chunk in re.split(r"\n\s*\n", hb04_markdown().strip()):
        chunk = " ".join(chunk.split())
        m = re.match(r"^#+\s+(.*)$", chunk)
        blocks.append(("heading", m.group(1)) if m else ("para", chunk))
    return blocks


def wrap(text: str, width: int = LINE_WIDTH) -> list:
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    return lines + [line] if line else lines


def layout(blocks: list, lines_per_page: int = LINES_PER_PAGE) -> list:
    """Pages (lists of lines) from blocks; a blank line separates blocks; a block may continue on the next page."""
    pages, current = [], []
    for _, text in blocks:
        for line in wrap(text) + [""]:
            if len(current) >= lines_per_page:
                pages.append(current)
                current = []
            current.append(line)
    if current:
        pages.append(current)
    return pages


# --- A minimal PDF writer ------------------------------------------------------------------------------------------

def _escape(line: str) -> bytes:
    data = line.encode("cp1252", errors="replace")
    return data.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _text_stream(lines: list) -> bytes:
    out = [b"BT /F1 10.5 Tf 14 TL 56 740 Td"]
    for line in lines:
        out.append(b"(" + _escape(line) + b") Tj T*")
    out.append(b"ET")
    return b"\n".join(out)


def _image_stream() -> bytes:
    """A page that is one picture and no text: an 8x8 grey inline image scaled over the page."""
    pixels = bytes((x * 32 + y * 4) % 256 for y in range(8) for x in range(8))
    return b"q 500 0 0 700 56 50 cm\nBI /W 8 /H 8 /CS /G /BPC 8 ID " + pixels + b"\nEI\nQ"


def pdf_from_streams(streams: list) -> bytes:
    """A valid PDF with one page per content stream (bytes)."""
    n = len(streams)
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               ("<< /Type /Pages /Kids [" + " ".join(f"{4 + 2 * i} 0 R" for i in range(n)) + f"] /Count {n} >>").encode(),
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    for i, stream in enumerate(streams):
        objects.append(("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> "
                        f"/Contents {5 + 2 * i} 0 R >>").encode())
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def text_pdf(pages: list) -> bytes:
    """pages: a list of pages, each a list of lines of text."""
    return pdf_from_streams([_text_stream(lines) for lines in pages])


def hb04_pdf(lines_per_page: int = LINES_PER_PAGE) -> bytes:
    return text_pdf(layout(hb04_blocks(), lines_per_page))


def image_only_pdf(pages: int = 1) -> bytes:
    return pdf_from_streams([_image_stream()] * pages)


def partial_scan_pdf() -> bytes:
    """Three pages: text, an image-only page, text."""
    pages = layout(hb04_blocks(), 12)
    return pdf_from_streams([_text_stream(pages[0]), _image_stream(), _text_stream(pages[1])])


# --- DOCX ----------------------------------------------------------------------------------------------------------

def tiny_png() -> bytes:
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * 4 for _ in range(4))
    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def hb04_docx(with_extras: bool = False) -> bytes:
    """HB-04 as a Word document. with_extras adds a table, a header and footer, and a picture, to exercise skipping."""
    import docx
    document = docx.Document()
    for kind, text in hb04_blocks():
        if kind == "heading":
            document.add_heading(text, level=1 if text.startswith("Proposal") else 2)
        else:
            document.add_paragraph(text)
    if with_extras:
        document.sections[0].header.paragraphs[0].text = "CONFIDENTIAL HEADER TEXT"
        document.sections[0].footer.paragraphs[0].text = "FOOTER PAGE TEXT"
        table = document.add_table(rows=2, cols=3)
        for cell, text in zip(table.rows[0].cells, ["Capability", "Scope", "Approval"]):
            cell.text = text
        for cell, text in zip(table.rows[1].cells, ["Payout ledger connector", "Singapore", "No named exception approved"]):
            cell.text = text
        document.add_picture(io.BytesIO(tiny_png()))
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def docx_with_tracked_changes() -> bytes:
    import docx
    from docx.oxml import parse_xml
    document = docx.Document()
    p = document.add_paragraph("The connector will handle ")
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    p._p.append(parse_xml(f'<w:del xmlns:w="{w}" w:id="1" w:author="x" w:date="2026-10-01T00:00:00Z"><w:r><w:delText>10,000</w:delText></w:r></w:del>'))
    p._p.append(parse_xml(f'<w:ins xmlns:w="{w}" w:id="2" w:author="x" w:date="2026-10-01T00:00:00Z"><w:r><w:t>12,000</w:t></w:r></w:ins>'))
    p.add_run(" payouts per day.")
    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


def main(argv: list) -> int:
    if len(argv) != 1:
        print("usage: python tests/fixtures/make_formats.py OUT_DIR", file=sys.stderr)
        return 2
    out = Path(argv[0]).resolve()
    if out.is_relative_to(config.DATA_DIR.resolve()):
        print("refused: write the fixtures outside the data folder", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    for name, data in (("hb04.pdf", hb04_pdf()), ("hb04.docx", hb04_docx()), ("image_only.pdf", image_only_pdf()),
                       ("partial_scan.pdf", partial_scan_pdf())):
        (out / name).write_bytes(data)
        print(f"wrote {out / name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
