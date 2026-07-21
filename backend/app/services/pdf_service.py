from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from PIL import Image as PILImage

RED = colors.HexColor("#C5161D")
CHARCOAL = colors.HexColor("#15191F")
GRAY = colors.HexColor("#667085")
LIGHT = colors.HexColor("#F4F5F7")
BORDER = colors.HexColor("#D9DDE3")


def _page(canvas: Any, document: Any) -> None:
    page = canvas
    doc = document
    width, height = A4
    page.saveState()
    page.setFillColor(CHARCOAL)
    page.rect(0, height - 27 * mm, width, 27 * mm, fill=1, stroke=0)
    page.setFillColor(RED)
    page.rect(0, height - 29 * mm, width, 2 * mm, fill=1, stroke=0)
    page.setFillColor(colors.white)
    page.setFont("Helvetica-BoldOblique", 20)
    page.drawString(18 * mm, height - 17 * mm, "ASSIS")
    page.setFont("Helvetica-Bold", 10)
    page.drawString(48 * mm, height - 17 * mm, "CARRETAS")
    page.setFillColor(GRAY)
    page.setFont("Helvetica", 7.5)
    page.drawString(18 * mm, 12 * mm, "Documento emitido pelo sistema Assis Carretas")
    page.drawRightString(width - 18 * mm, 12 * mm, f"Página {doc.page}")
    page.setStrokeColor(BORDER)
    page.line(18 * mm, 16 * mm, width - 18 * mm, 16 * mm)
    page.restoreState()


def simple_pdf(title: str, lines: list[str], signature_content: bytes | None = None) -> bytes:
    """Gera um PDF A4 profissional com marca, seções, dados e assinatura."""
    buffer = BytesIO()
    width, height = A4
    doc = BaseDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=37 * mm,
        bottomMargin=23 * mm,
        title=title,
        pdfVersion=(1, 4),
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")
    doc.addPageTemplates([PageTemplate(id="document", frames=[frame], onPage=_page)])

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocumentTitle", parent=styles["Title"], fontName="Helvetica-Bold",
        fontSize=18, leading=22, textColor=CHARCOAL, alignment=TA_CENTER, spaceAfter=4 * mm,
    )
    intro_style = ParagraphStyle(
        "Intro", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.5,
        leading=14, textColor=CHARCOAL, alignment=TA_JUSTIFY, spaceAfter=2.5 * mm,
    )
    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5,
        leading=13, textColor=colors.white, leftIndent=3 * mm, spaceBefore=4 * mm,
        spaceAfter=2 * mm, backColor=CHARCOAL, borderPadding=(2.5 * mm, 3 * mm, 2.5 * mm, 3 * mm),
    )
    note_style = ParagraphStyle(
        "Note", parent=intro_style, fontSize=8, leading=11, textColor=GRAY,
    )
    story: list[object] = [
        Paragraph(title.upper(), title_style),
        Table(
            [["DOCUMENTO DIGITAL", "Integridade, checklist e assinatura armazenados"]],
            colWidths=[42 * mm, width - 78 * mm],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), RED), ("TEXTCOLOR", (0, 0), (0, 0), colors.white),
                ("FONTNAME", (0, 0), (0, 0), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, 0), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (1, 0), (1, 0), LIGHT), ("TEXTCOLOR", (1, 0), (1, 0), GRAY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
            ]),
        ),
        Spacer(1, 4 * mm),
    ]

    sections = {
        "CONTRATO DE LOCAÇÃO E RESPONSABILIDADE", "CHECKLIST DE INTEGRIDADE:",
        "RECIBO DE PAGAMENTO", "RECIBO DE COBRANÇAS EXTRAS", "COMPOSIÇÃO FINANCEIRA:",
        "ITENS ADICIONAIS:",
    }
    detail_rows: list[list[object]] = []

    def flush_details() -> None:
        if not detail_rows:
            return
        story.append(Table(
            detail_rows.copy(), colWidths=[46 * mm, doc.width - 46 * mm],
            style=TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, BORDER),
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("TEXTCOLOR", (0, 0), (0, -1), CHARCOAL),
                ("TEXTCOLOR", (1, 0), (1, -1), CHARCOAL),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
            ]),
        ))
        story.append(Spacer(1, 2.5 * mm))
        detail_rows.clear()

    for line in lines:
        if line in sections:
            flush_details()
            story.append(Paragraph(line.rstrip(":"), section_style))
        elif ":" in line and len(line.split(":", 1)[0]) <= 28:
            label, value = line.split(":", 1)
            detail_rows.append([Paragraph(label, note_style), Paragraph(value.strip(), note_style)])
        else:
            flush_details()
            story.append(Paragraph(line, intro_style))
    flush_details()

    if signature_content:
        signature_buffer = BytesIO()
        with PILImage.open(BytesIO(signature_content)).convert("RGBA") as source_signature:
            white_background = PILImage.new("RGBA", source_signature.size, "white")
            white_background.alpha_composite(source_signature)
            white_background.convert("RGB").save(signature_buffer, format="PNG")
        signature_buffer.seek(0)
        signature = Image(signature_buffer)
        signature._restrictSize(72 * mm, 25 * mm)
        signature_block = Table(
            [[Paragraph("ASSINATURA DO CLIENTE", note_style)], [signature],
             [Paragraph("Assinatura eletrônica vinculada ao checklist e ao documento.", note_style)]],
            colWidths=[90 * mm],
            style=TableStyle([
                ("BOX", (0, 0), (-1, -1), 0.7, BORDER),
                ("BACKGROUND", (0, 0), (0, 0), LIGHT),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]),
        )
        story.extend([Spacer(1, 5 * mm), KeepTogether(signature_block)])

    doc.build(story)
    return buffer.getvalue()
