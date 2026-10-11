"""Office Document Conversion Engine supporting native Python (python-docx, reportlab, openpyxl, python-pptx) and LibreOffice."""

from pathlib import Path
import csv
import json
import html
import re
import logging
from typing import Callable, Optional, Dict, Any, List

from omniconvert.engines.base import BaseEngine
from omniconvert.engines.office_detector import LibreOfficeDetector
from omniconvert.models.conversion_job import ConversionJob, JobProgress
from omniconvert.core.safe_subprocess import SafeSubprocessRunner

logger = logging.getLogger(__name__)


class OfficeEngine(BaseEngine):
    """
    Converts Office and document formats:
    - DOCX <-> PDF, TXT, HTML, Markdown
    - XLSX <-> PDF, CSV, JSON, HTML
    - PPTX -> PDF, TXT
    - TXT / Markdown / HTML / RTF -> PDF, DOCX
    Uses headless LibreOffice when available, and falls back to built-in pure-Python
    document engines (python-docx, reportlab, openpyxl, python-pptx) so conversions
    work 100% offline even without LibreOffice installed.
    """

    def __init__(self, custom_path: Optional[str] = None):
        self.detector = LibreOfficeDetector(custom_path)
        self.info = self.detector.detect()
        self._runner = SafeSubprocessRunner()

    @property
    def name(self) -> str:
        return "libreoffice"

    def is_native_available(self) -> bool:
        try:
            import docx
            import reportlab
            return True
        except ImportError:
            return False

    def is_available(self) -> bool:
        return self.info.is_available or self.is_native_available()

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        if not self.is_available():
            raise RuntimeError(f"Office engine is not available: {self.info.error_message}")

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled before start.")

        source = job.source_path
        src_ext = source.suffix.lower().lstrip(".")
        target_format = job.target_format.lower().lstrip(".")
        settings = job.settings or {}

        if progress_callback:
            progress_callback(JobProgress(percentage=15.0, stage="Reading Document", detail=f"Processing {source.name}"))

        # 1. If LibreOffice is installed and target is pdf/txt/docx/odt, try LibreOffice first for legacy formats (.doc, .odt, .rtf)
        if self.info.is_available and src_ext in ("doc", "odt", "rtf", "odp", "ods"):
            try:
                return self._execute_libreoffice(source, target_format, workspace_dir, progress_callback, is_cancelled)
            except Exception as e:
                logger.warning("LibreOffice conversion failed, trying native fallback: %s", e)

        # 2. Native Python conversions for DOCX, XLSX, PPTX, TXT, MD, HTML, RTF, CSV, JSON
        if target_format == "pdf":
            if src_ext == "docx":
                return self._docx_to_pdf(source, workspace_dir, settings, progress_callback, is_cancelled)
            elif src_ext == "xlsx":
                return self._xlsx_to_pdf(source, workspace_dir, settings, progress_callback, is_cancelled)
            elif src_ext == "pptx":
                return self._pptx_to_pdf(source, workspace_dir, settings, progress_callback, is_cancelled)
            elif src_ext in ("txt", "md", "markdown", "html", "htm", "rtf"):
                return self._text_or_md_to_pdf(source, src_ext, workspace_dir, settings, progress_callback, is_cancelled)
            elif self.info.is_available:
                return self._execute_libreoffice(source, target_format, workspace_dir, progress_callback, is_cancelled)

        elif target_format == "docx":
            if src_ext in ("txt", "md", "markdown", "html", "htm", "rtf"):
                return self._text_or_md_to_docx(source, src_ext, workspace_dir, settings, progress_callback, is_cancelled)
            elif self.info.is_available:
                return self._execute_libreoffice(source, target_format, workspace_dir, progress_callback, is_cancelled)

        elif target_format == "txt":
            if src_ext == "docx":
                return self._docx_to_txt(source, workspace_dir, progress_callback, is_cancelled)
            elif src_ext == "pptx":
                return self._pptx_to_txt(source, workspace_dir, progress_callback, is_cancelled)
            elif src_ext == "xlsx":
                return self._xlsx_to_csv(source, workspace_dir, target_ext="txt", progress_callback=progress_callback, is_cancelled=is_cancelled)
            elif src_ext in ("rtf", "html", "htm", "md", "markdown"):
                return self._markup_to_txt(source, src_ext, workspace_dir)

        elif target_format == "html":
            if src_ext == "docx":
                return self._docx_to_html(source, workspace_dir, progress_callback, is_cancelled)
            elif src_ext in ("md", "markdown"):
                return self._md_to_html(source, workspace_dir)
            elif src_ext == "xlsx":
                return self._xlsx_to_html(source, workspace_dir)

        elif target_format in ("md", "markdown"):
            if src_ext == "docx":
                return self._docx_to_md(source, workspace_dir, progress_callback, is_cancelled)
            elif src_ext in ("html", "htm"):
                return self._html_to_md(source, workspace_dir)

        elif target_format == "csv":
            if src_ext == "xlsx":
                return self._xlsx_to_csv(source, workspace_dir, target_ext="csv", progress_callback=progress_callback, is_cancelled=is_cancelled)

        elif target_format == "json":
            if src_ext == "xlsx":
                return self._xlsx_to_json(source, workspace_dir, progress_callback, is_cancelled)

        elif target_format == "xlsx":
            if src_ext in ("csv", "tsv", "json"):
                return self._data_to_xlsx(source, src_ext, workspace_dir, progress_callback, is_cancelled)

        # Fallback to LibreOffice if available
        if self.info.is_available:
            return self._execute_libreoffice(source, target_format, workspace_dir, progress_callback, is_cancelled)

        raise ValueError(f"Unsupported document conversion route: .{src_ext} -> .{target_format}")

    def _execute_libreoffice(
        self,
        source: Path,
        target_format: str,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        filter_spec = target_format
        if target_format == "txt":
            filter_spec = "txt:Text"

        args = [
            str(self.info.soffice_path),
            "--headless",
            "--invisible",
            "--nologo",
            "--nofirststartwizard",
            "--convert-to", filter_spec,
            "--outdir", str(workspace_dir),
            str(source)
        ]

        res = self._runner.run(args, timeout=120.0, is_cancelled=is_cancelled)
        if res.cancelled or (is_cancelled and is_cancelled()):
            raise InterruptedError("Job cancelled by user.")
        if res.timed_out:
            raise TimeoutError("LibreOffice document conversion timed out.")
        if res.returncode != 0:
            err = res.stderr.strip() or "LibreOffice failed to convert document."
            raise RuntimeError(f"Document conversion failed: {err}")

        expected_target = workspace_dir / f"{source.stem}.{target_format}"
        if not expected_target.exists():
            matches = list(workspace_dir.glob(f"*.{target_format}"))
            if matches:
                expected_target = matches[0]
            else:
                raise FileNotFoundError(f"Expected converted document not found in workspace: {expected_target}")
        return expected_target

    def _iter_docx_blocks(self, doc):
        """Yield ('paragraph', Paragraph) and ('table', Table) in exact document body order."""
        from docx.text.paragraph import Paragraph as DocxParagraph
        from docx.table import Table as DocxTable

        if hasattr(doc, "iter_inner_content"):
            for item in doc.iter_inner_content():
                if isinstance(item, DocxParagraph):
                    yield "paragraph", item
                elif isinstance(item, DocxTable):
                    yield "table", item
            return

        for child in doc.element.body.iterchildren():
            if child.tag.endswith("}p"):
                yield "paragraph", DocxParagraph(child, doc)
            elif child.tag.endswith("}tbl"):
                yield "table", DocxTable(child, doc)

    def _docx_to_pdf(
        self,
        source: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Render a Word (.docx) document into a formatted multi-page PDF using python-docx and ReportLab."""
        import docx
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

        target_file = workspace_dir / f"{source.stem}.pdf"
        try:
            doc = docx.Document(str(source))
        except Exception as e:
            raise ValueError(f"Could not open Word document (.docx): {e}")

        page_size = A4 if str(settings.get("page_size", "letter")).lower() == "a4" else letter
        pdf_doc = SimpleDocTemplate(
            str(target_file),
            pagesize=page_size,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=source.stem
        )

        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            "OmniBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            spaceAfter=8
        )
        h1_style = ParagraphStyle(
            "OmniH1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            spaceBefore=12,
            spaceAfter=8
        )
        h2_style = ParagraphStyle(
            "OmniH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            spaceBefore=10,
            spaceAfter=6
        )
        h3_style = ParagraphStyle(
            "OmniH3",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            spaceBefore=8,
            spaceAfter=4
        )

        story = []

        # Extract embedded images from relationships if present
        embedded_images: List[Path] = []
        preset = str(settings.get("quality_preset", "lossless")).lower()
        if preset in ("lossless", "exact", "high", "balanced"):
            try:
                for rel_id, rel in doc.part.rels.items():
                    if "image" in rel.target_ref:
                        img_part = rel.target_part
                        img_path = workspace_dir / f"docx_img_{rel_id}.png"
                        img_path.write_bytes(img_part.blob)
                        embedded_images.append(img_path)
            except Exception:
                pass

        # Iterate through document body elements in exact document order (interleaved paragraphs and tables)
        blocks = list(self._iter_docx_blocks(doc))
        total_blocks = max(len(blocks), 1)
        for idx, (b_type, block) in enumerate(blocks):
            if is_cancelled and is_cancelled():
                raise InterruptedError("Cancelled during DOCX-to-PDF conversion.")

            if b_type == "paragraph":
                para = block
                text = para.text.strip()
                if not text:
                    story.append(Spacer(1, 6))
                    continue

                style_name = (para.style.name if para.style else "Normal").lower()
                formatted_runs = []
                for run in para.runs:
                    r_txt = html.escape(run.text)
                    if not r_txt:
                        continue
                    if run.bold:
                        r_txt = f"<b>{r_txt}</b>"
                    if run.italic:
                        r_txt = f"<i>{r_txt}</i>"
                    if run.underline:
                        r_txt = f"<u>{r_txt}</u>"
                    formatted_runs.append(r_txt)

                markup = "".join(formatted_runs) if formatted_runs else html.escape(text)
                markup = markup.replace("\n", "<br/>")

                if "heading 1" in style_name or "title" in style_name:
                    story.append(Paragraph(markup, h1_style))
                elif "heading 2" in style_name:
                    story.append(Paragraph(markup, h2_style))
                elif "heading 3" in style_name:
                    story.append(Paragraph(markup, h3_style))
                else:
                    story.append(Paragraph(markup, body_style))

            elif b_type == "table":
                tbl = block
                table_data = []
                for row in tbl.rows:
                    row_cells = [Paragraph(html.escape(cell.text.strip()), body_style) for cell in row.cells]
                    if row_cells:
                        table_data.append(row_cells)
                if table_data:
                    t = Table(table_data, repeatRows=1)
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("PADDING", (0, 0), (-1, -1), 6),
                    ]))
                    story.append(Spacer(1, 8))
                    story.append(t)
                    story.append(Spacer(1, 8))

            if progress_callback and idx % 10 == 0:
                progress_callback(JobProgress(
                    percentage=20.0 + (idx / total_blocks) * 50.0,
                    stage="Formatting Document Elements",
                    detail=f"Element {idx + 1}/{total_blocks}"
                ))

        # Append embedded images preserving aspect ratio
        for img_p in embedded_images:
            try:
                from PIL import Image as PILImage
                with PILImage.open(img_p) as pim:
                    w, h = pim.size
                max_w = 5.5 * inch
                scale = min(1.0, max_w / max(w, 1))
                story.append(Spacer(1, 8))
                story.append(RLImage(str(img_p), width=w * scale, height=h * scale))
            except Exception:
                pass

        if not story:
            story.append(Paragraph("&nbsp;", body_style))

        if progress_callback:
            progress_callback(JobProgress(percentage=85.0, stage="Building PDF", detail="Writing PDF pages"))

        pdf_doc.build(story)
        return target_file

    def _docx_to_txt(
        self,
        source: Path,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        import docx
        target_file = workspace_dir / f"{source.stem}.txt"
        doc = docx.Document(str(source))
        lines = []
        for b_type, block in self._iter_docx_blocks(doc):
            if b_type == "paragraph":
                lines.append(block.text)
            elif b_type == "table":
                for row in block.rows:
                    lines.append("\t".join(c.text.strip() for c in row.cells))
        content = "\n".join(lines)
        if not content.strip():
            content = " "
        target_file.write_text(content, encoding="utf-8")
        return target_file

    def _docx_to_html(
        self,
        source: Path,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        import docx
        target_file = workspace_dir / f"{source.stem}.html"
        doc = docx.Document(str(source))
        parts = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'>",
            f"<title>{html.escape(source.stem)}</title>",
            "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:800px;margin:32px auto;line-height:1.6;color:#1f2937;}",
            "table{border-collapse:collapse;width:100%;margin:16px 0;}th,td{border:1px solid #d1d5db;padding:8px;text-align:left;}</style>",
            "</head><body>"
        ]
        for b_type, block in self._iter_docx_blocks(doc):
            if b_type == "paragraph":
                p = block
                txt = html.escape(p.text)
                if not txt.strip():
                    continue
                sname = (p.style.name if p.style else "").lower()
                if "heading 1" in sname or "title" in sname:
                    parts.append(f"<h1>{txt}</h1>")
                elif "heading 2" in sname:
                    parts.append(f"<h2>{txt}</h2>")
                elif "heading 3" in sname:
                    parts.append(f"<h3>{txt}</h3>")
                else:
                    parts.append(f"<p>{txt}</p>")
            elif b_type == "table":
                parts.append("<table>")
                for r in block.rows:
                    cells = "".join(f"<td>{html.escape(c.text.strip())}</td>" for c in r.cells)
                    parts.append(f"<tr>{cells}</tr>")
                parts.append("</table>")
        parts.append("</body></html>")
        target_file.write_text("\n".join(parts), encoding="utf-8")
        return target_file

    def _docx_to_md(
        self,
        source: Path,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        import docx
        target_file = workspace_dir / f"{source.stem}.md"
        doc = docx.Document(str(source))
        lines = []
        for b_type, block in self._iter_docx_blocks(doc):
            if b_type == "paragraph":
                p = block
                txt = p.text.strip()
                if not txt:
                    continue
                sname = (p.style.name if p.style else "").lower()
                if "heading 1" in sname or "title" in sname:
                    lines.append(f"# {txt}")
                elif "heading 2" in sname:
                    lines.append(f"## {txt}")
                elif "heading 3" in sname:
                    lines.append(f"### {txt}")
                elif "list" in sname:
                    lines.append(f"- {txt}")
                else:
                    lines.append(txt)
            elif b_type == "table":
                md_rows = []
                for r_idx, row in enumerate(block.rows):
                    cell_texts = [c.text.strip().replace("\n", " ").replace("|", "\\|") for c in row.cells]
                    if not cell_texts:
                        continue
                    md_rows.append("| " + " | ".join(cell_texts) + " |")
                    if r_idx == 0:
                        md_rows.append("| " + " | ".join("---" for _ in cell_texts) + " |")
                if md_rows:
                    lines.append("\n".join(md_rows))
        content = "\n\n".join(lines).strip() or f"# {source.stem}"
        target_file.write_text(content + "\n", encoding="utf-8")
        return target_file

    def _text_or_md_to_docx(
        self,
        source: Path,
        src_ext: str,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Convert TXT, Markdown, or HTML into a structured Word (.docx) document."""
        import docx
        target_file = workspace_dir / f"{source.stem}.docx"
        raw_text = source.read_text(encoding="utf-8", errors="replace")

        if src_ext in ("html", "htm"):
            raw_text = re.sub(r"<[^>]+>", "", raw_text)

        doc = docx.Document()
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                doc.add_paragraph("")
            elif stripped.startswith("# "):
                doc.add_heading(stripped[2:].strip(), level=1)
            elif stripped.startswith("## "):
                doc.add_heading(stripped[3:].strip(), level=2)
            elif stripped.startswith("### "):
                doc.add_heading(stripped[4:].strip(), level=3)
            elif stripped.startswith(("- ", "* ")):
                doc.add_paragraph(stripped[2:].strip(), style="List Bullet")
            else:
                doc.add_paragraph(line)

        doc.save(str(target_file))
        return target_file

    def _text_or_md_to_pdf(
        self,
        source: Path,
        src_ext: str,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Render TXT, Markdown, HTML, or RTF into a formatted multi-page PDF."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

        target_file = workspace_dir / f"{source.stem}.pdf"
        raw_text = source.read_text(encoding="utf-8", errors="replace")
        if src_ext in ("html", "htm"):
            raw_text = re.sub(r"<[^>]+>", "", raw_text)

        pdf_doc = SimpleDocTemplate(
            str(target_file),
            pagesize=letter,
            leftMargin=0.75 * inch,
            rightMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=source.stem
        )
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle("Body", parent=styles["Normal"], fontName="Helvetica", fontSize=11, leading=15, spaceAfter=6)
        h1_style = ParagraphStyle("H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=8)
        h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=6)

        story = []
        for line in raw_text.splitlines():
            s = line.strip()
            if not s:
                story.append(Spacer(1, 6))
            elif s.startswith("# "):
                story.append(Paragraph(html.escape(s[2:].strip()), h1_style))
            elif s.startswith("## "):
                story.append(Paragraph(html.escape(s[3:].strip()), h2_style))
            else:
                story.append(Paragraph(html.escape(line), body_style))

        if not story:
            story.append(Paragraph("&nbsp;", body_style))

        pdf_doc.build(story)
        return target_file

    def _xlsx_to_pdf(
        self,
        source: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Render Excel (.xlsx) workbook sheets into a formatted PDF report."""
        import openpyxl
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        target_file = workspace_dir / f"{source.stem}.pdf"
        wb = openpyxl.load_workbook(str(source), data_only=True)
        pdf_doc = SimpleDocTemplate(str(target_file), pagesize=landscape(letter), title=source.stem)
        styles = getSampleStyleSheet()
        story = []

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
            story.append(Paragraph(f"<b>Sheet: {html.escape(sheet_name)}</b>", styles["Heading2"]))
            story.append(Spacer(1, 6))
            rows_data = []
            for row in ws.iter_rows(values_only=True):
                if any(v is not None for v in row):
                    rows_data.append([str(v) if v is not None else "" for v in row])
            if rows_data:
                t = Table(rows_data, repeatRows=1)
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
            story.append(Spacer(1, 14))

        if not story:
            story.append(Paragraph("Empty Workbook", styles["Normal"]))
        pdf_doc.build(story)
        return target_file

    def _xlsx_to_csv(self, source: Path, workspace_dir: Path, target_ext: str = "csv", progress_callback=None, is_cancelled=None) -> Path:
        import openpyxl
        target_file = workspace_dir / f"{source.stem}.{target_ext}"
        wb = openpyxl.load_workbook(str(source), data_only=True)
        ws = wb.active
        with open(target_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for row in ws.iter_rows(values_only=True):
                writer.writerow(["" if v is None else v for v in row])
        return target_file

    def _xlsx_to_json(self, source: Path, workspace_dir: Path, progress_callback=None, is_cancelled=None) -> Path:
        import openpyxl
        target_file = workspace_dir / f"{source.stem}.json"
        wb = openpyxl.load_workbook(str(source), data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            target_file.write_text("[]", encoding="utf-8")
            return target_file
        headers = [str(h) if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
        items = []
        for r in rows[1:]:
            if any(v is not None for v in r):
                items.append({headers[i]: r[i] for i in range(min(len(headers), len(r)))})
        target_file.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
        return target_file

    def _xlsx_to_html(self, source: Path, workspace_dir: Path) -> Path:
        import openpyxl
        target_file = workspace_dir / f"{source.stem}.html"
        wb = openpyxl.load_workbook(str(source), data_only=True)
        parts = ["<!DOCTYPE html><html><head><meta charset='utf-8'><style>table{border-collapse:collapse;}td,th{border:1px solid #ccc;padding:6px;}</style></head><body>"]
        for name in wb.sheetnames:
            ws = wb[name]
            parts.append(f"<h2>{html.escape(name)}</h2><table>")
            for row in ws.iter_rows(values_only=True):
                cells = "".join(f"<td>{html.escape(str(v) if v is not None else '')}</td>" for v in row)
                parts.append(f"<tr>{cells}</tr>")
            parts.append("</table>")
        parts.append("</body></html>")
        target_file.write_text("\n".join(parts), encoding="utf-8")
        return target_file

    def _data_to_xlsx(self, source: Path, src_ext: str, workspace_dir: Path, progress_callback=None, is_cancelled=None) -> Path:
        import openpyxl
        from openpyxl.styles import Font
        target_file = workspace_dir / f"{source.stem}.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Data"

        if src_ext in ("csv", "tsv"):
            delim = "\t" if src_ext == "tsv" else ","
            with open(source, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.reader(f, delimiter=delim)
                for row in reader:
                    ws.append(row)
        elif src_ext == "json":
            data = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data = [data]
            if isinstance(data, list) and data and isinstance(data[0], dict):
                headers = list(data[0].keys())
                ws.append(headers)
                for item in data:
                    ws.append([str(item.get(h, "")) if isinstance(item.get(h), (dict, list)) else item.get(h, "") for h in headers])

        if ws.max_row >= 1:
            for cell in ws[1]:
                cell.font = Font(bold=True)

        wb.save(str(target_file))
        return target_file

    def _pptx_to_pdf(self, source: Path, workspace_dir: Path, settings: Dict[str, Any], progress_callback=None, is_cancelled=None) -> Path:
        from pptx import Presentation
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle

        target_file = workspace_dir / f"{source.stem}.pdf"
        prs = Presentation(str(source))
        pdf_doc = SimpleDocTemplate(str(target_file), pagesize=landscape(letter), title=source.stem)
        styles = getSampleStyleSheet()
        story = []

        for idx, slide in enumerate(prs.slides):
            if idx > 0:
                story.append(PageBreak())
            story.append(Paragraph(f"<b>Slide {idx + 1}</b>", styles["Heading2"]))
            story.append(Spacer(1, 10))
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    for p in shape.text_frame.paragraphs:
                        txt = p.text.strip()
                        if txt:
                            story.append(Paragraph(html.escape(txt), styles["Normal"]))
                            story.append(Spacer(1, 4))
                if getattr(shape, "has_table", False):
                    rows_data = []
                    for row in shape.table.rows:
                        rows_data.append([Paragraph(html.escape(cell.text.strip()), styles["Normal"]) for cell in row.cells])
                    if rows_data:
                        t = Table(rows_data, repeatRows=1)
                        t.setStyle(TableStyle([
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
                            ("PADDING", (0, 0), (-1, -1), 5),
                        ]))
                        story.append(t)
                        story.append(Spacer(1, 8))
            if getattr(slide, "has_notes_slide", False) and slide.notes_slide and slide.notes_slide.notes_text_frame:
                notes_txt = slide.notes_slide.notes_text_frame.text.strip()
                if notes_txt:
                    story.append(Spacer(1, 6))
                    story.append(Paragraph(f"<i>Speaker Notes: {html.escape(notes_txt)}</i>", styles["Normal"]))

        if not story:
            story.append(Paragraph("Empty Presentation", styles["Normal"]))
        pdf_doc.build(story)
        return target_file

    def _pptx_to_txt(self, source: Path, workspace_dir: Path, progress_callback=None, is_cancelled=None) -> Path:
        from pptx import Presentation
        target_file = workspace_dir / f"{source.stem}.txt"
        prs = Presentation(str(source))
        slides_text = []
        for idx, slide in enumerate(prs.slides):
            lines = [f"--- Slide {idx + 1} ---"]
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    txt = shape.text_frame.text.strip()
                    if txt:
                        lines.append(txt)
                if getattr(shape, "has_table", False):
                    for row in shape.table.rows:
                        lines.append("\t".join(cell.text.strip() for cell in row.cells))
            if getattr(slide, "has_notes_slide", False) and slide.notes_slide and slide.notes_slide.notes_text_frame:
                notes_txt = slide.notes_slide.notes_text_frame.text.strip()
                if notes_txt:
                    lines.append(f"[Speaker Notes] {notes_txt}")
            slides_text.append("\n".join(lines))
        target_file.write_text("\n\n".join(slides_text) or " ", encoding="utf-8")
        return target_file

    def _md_to_html(self, source: Path, workspace_dir: Path) -> Path:
        import markdown as md_lib
        target_file = workspace_dir / f"{source.stem}.html"
        raw = source.read_text(encoding="utf-8", errors="replace")
        body = md_lib.markdown(raw, extensions=["tables", "fenced_code"])
        html_doc = f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{html.escape(source.stem)}</title></head><body>{body}</body></html>"
        target_file.write_text(html_doc, encoding="utf-8")
        return target_file

    def _html_to_md(self, source: Path, workspace_dir: Path) -> Path:
        target_file = workspace_dir / f"{source.stem}.md"
        raw = source.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n", raw, flags=re.I | re.S)
        text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n", text, flags=re.I | re.S)
        text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n", text, flags=re.I | re.S)
        text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", "", text)
        target_file.write_text(html.unescape(text).strip() + "\n", encoding="utf-8")
        return target_file

    def _markup_to_txt(self, source: Path, src_ext: str, workspace_dir: Path) -> Path:
        target_file = workspace_dir / f"{source.stem}.txt"
        raw = source.read_text(encoding="utf-8", errors="replace")
        if src_ext in ("html", "htm"):
            raw = html.unescape(re.sub(r"<[^>]+>", "", raw))
        target_file.write_text(raw, encoding="utf-8")
        return target_file
