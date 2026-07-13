from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    ListFlowable,
    ListItem,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "kyc_api_documentation.md"
OUTPUT = ROOT / "output" / "pdf" / "kyc_api_frontend_integration_documentation.pdf"


def paragraph_text(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("`", "")
    )


def make_styles():
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "KycTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17202A"),
            spaceAfter=8,
        ),
        "H1": ParagraphStyle(
            "KycH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#17202A"),
            spaceBefore=12,
            spaceAfter=7,
        ),
        "H2": ParagraphStyle(
            "KycH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#1F3A5A"),
            spaceBefore=9,
            spaceAfter=5,
        ),
        "H3": ParagraphStyle(
            "KycH3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#263849"),
            spaceBefore=6,
            spaceAfter=3,
        ),
        "Body": ParagraphStyle(
            "KycBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.7,
            leading=12.1,
            textColor=colors.HexColor("#25313D"),
            spaceAfter=5,
        ),
        "TableCell": ParagraphStyle(
            "KycTableCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.1,
            leading=9.1,
            textColor=colors.HexColor("#25313D"),
        ),
        "Code": ParagraphStyle(
            "KycCode",
            parent=base["Code"],
            fontName="Courier",
            fontSize=6.8,
            leading=8.3,
            textColor=colors.HexColor("#1D2733"),
            backColor=colors.HexColor("#F4F6F8"),
            borderColor=colors.HexColor("#D7DEE8"),
            borderWidth=0.3,
            borderPadding=5,
            spaceBefore=2,
            spaceAfter=6,
        ),
    }


def split_table_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_widths(column_count):
    total = 180 * mm
    if column_count == 2:
        return [48 * mm, 132 * mm]
    if column_count == 3:
        return [44 * mm, 28 * mm, 108 * mm]
    return [total / column_count] * column_count


def render_table(rows, styles):
    converted = []
    for row in rows:
        converted.append([Paragraph(paragraph_text(cell), styles["TableCell"]) for cell in row])

    table = Table(
        converted,
        colWidths=table_widths(len(rows[0])),
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D4DAE3")),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#243447")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [table, Spacer(1, 5)]


def render_markdown(markdown, styles):
    flow = []
    lines = markdown.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]

        if not line.strip():
            index += 1
            continue

        if line.startswith("```"):
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].startswith("```"):
                code_lines.append(lines[index])
                index += 1
            flow.append(Preformatted("\n".join(code_lines), styles["Code"], maxLineLength=110))
            index += 1
            continue

        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            rows = [
                split_table_row(row)
                for row in table_lines
                if "---" not in row.replace(" ", "")
            ]
            if rows:
                flow.extend(render_table(rows, styles))
            continue

        if line.startswith("- "):
            items = []
            while index < len(lines) and lines[index].startswith("- "):
                items.append(Paragraph(paragraph_text(lines[index][2:]), styles["Body"]))
                index += 1
            flow.append(
                ListFlowable(
                    [ListItem(item, leftIndent=8) for item in items],
                    bulletType="bullet",
                    leftIndent=16,
                    bulletFontName="Helvetica",
                    bulletFontSize=7,
                )
            )
            flow.append(Spacer(1, 5))
            continue

        if line.startswith("# "):
            flow.append(Paragraph(paragraph_text(line[2:]), styles["Title"]))
        elif line.startswith("## "):
            flow.append(Paragraph(paragraph_text(line[3:]), styles["H1"]))
        elif line.startswith("### "):
            flow.append(Paragraph(paragraph_text(line[4:]), styles["H2"]))
        else:
            paragraph_lines = [line.strip()]
            index += 1
            while index < len(lines) and lines[index].strip() and not lines[index].startswith(("#", "|", "- ", "```")):
                paragraph_lines.append(lines[index].strip())
                index += 1
            flow.append(Paragraph(paragraph_text(" ".join(paragraph_lines)), styles["Body"]))
            continue

        index += 1

    return flow


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(colors.HexColor("#D6DCE5"))
    canvas.setLineWidth(0.4)
    canvas.line(16 * mm, height - 14 * mm, width - 16 * mm, height - 14 * mm)
    canvas.line(16 * mm, 13 * mm, width - 16 * mm, 13 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#5F6B78"))
    canvas.drawString(16 * mm, height - 10 * mm, "KYC API Documentation")
    canvas.drawRightString(width - 16 * mm, height - 10 * mm, "Frontend Integration")
    canvas.drawString(16 * mm, 8 * mm, "Generated from repository code on 2026-06-19")
    canvas.drawRightString(width - 16 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    styles = make_styles()
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title="KYC API Documentation",
        author="Generated from repository Markdown",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=header_footer)])
    doc.build(render_markdown(SOURCE.read_text(encoding="utf-8"), styles))


if __name__ == "__main__":
    build()
    print(OUTPUT)
