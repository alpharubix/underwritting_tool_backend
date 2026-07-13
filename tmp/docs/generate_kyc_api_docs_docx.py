from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "kyc_api_documentation.md"
OUTPUT = ROOT / "output" / "docs" / "kyc_api_frontend_integration_documentation.docx"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def run(text, bold=False, monospace=False):
    props = []
    if bold:
        props.append("<w:b/>")
    if monospace:
        props.append('<w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>')
        props.append('<w:sz w:val="18"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(str(text))}</w:t></w:r>'


def para(text="", style=None, bold=False, monospace=False):
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    body = []
    for index, line in enumerate(str(text).split("\n")):
        if index:
            body.append("<w:r><w:br/></w:r>")
        body.append(run(line, bold=bold, monospace=monospace))
    return f"<w:p>{ppr}{''.join(body)}</w:p>"


def code_block(text):
    return para(text, style="CodeBlock", monospace=True)


def cell(content, header=False):
    return (
        '<w:tc><w:tcPr><w:tcW w:w="2400" w:type="dxa"/>'
        '<w:tcMar><w:top w:w="80" w:type="dxa"/><w:left w:w="80" w:type="dxa"/>'
        '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="80" w:type="dxa"/></w:tcMar>'
        "</w:tcPr>"
        f"{para(content, bold=header)}"
        "</w:tc>"
    )


def table(rows):
    parts = [
        "<w:tbl>",
        '<w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/>'
        '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" '
        'w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>',
    ]
    for row_index, row in enumerate(rows):
        parts.append("<w:tr>")
        for value in row:
            parts.append(cell(value, header=row_index == 0))
        parts.append("</w:tr>")
    parts.append("</w:tbl>")
    parts.append(para(""))
    return "".join(parts)


def split_table_row(line):
    return [cell.strip().replace("`", "") for cell in line.strip().strip("|").split("|")]


def render_markdown(markdown):
    doc = []
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
            doc.append(code_block("\n".join(code_lines)))
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
                doc.append(table(rows))
            continue

        if line.startswith("- "):
            while index < len(lines) and lines[index].startswith("- "):
                doc.append(para(f"- {lines[index][2:].replace('`', '')}", style="ListParagraph"))
                index += 1
            continue

        if line.startswith("# "):
            doc.append(para(line[2:], style="Title"))
            index += 1
            continue

        if line.startswith("## "):
            doc.append(para(line[3:], style="Heading1"))
            index += 1
            continue

        if line.startswith("### "):
            doc.append(para(line[4:], style="Heading2"))
            index += 1
            continue

        paragraph_lines = [line.strip()]
        index += 1
        while index < len(lines) and lines[index].strip() and not lines[index].startswith(("#", "|", "- ", "```")):
            paragraph_lines.append(lines[index].strip())
            index += 1
        doc.append(para(" ".join(paragraph_lines).replace("`", "")))

    return "".join(doc)


def write_docx():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{NS["w"]}" xmlns:r="{NS["r"]}">'
        f"<w:body>{render_markdown(SOURCE.read_text(encoding='utf-8'))}"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1008" w:right="1008" w:bottom="1008" w:left="1008" '
        'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>"
    )
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    doc_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""
    styles = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{NS["w"]}">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="21"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/><w:qFormat/><w:pPr><w:jc w:val="center"/><w:spacing w:after="240"/></w:pPr><w:rPr><w:b/><w:sz w:val="40"/><w:color w:val="17202A"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="280" w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="30"/><w:color w:val="17202A"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="220" w:after="100"/></w:pPr><w:rPr><w:b/><w:sz w:val="25"/><w:color w:val="1F3A5A"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="CodeBlock"><w:name w:val="Code Block"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:before="80" w:after="160" w:line="240" w:lineRule="auto"/><w:ind w:left="180" w:right="180"/><w:shd w:val="clear" w:color="auto" w:fill="F4F6F8"/></w:pPr><w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/><w:sz w:val="18"/><w:color w:val="1D2733"/></w:rPr></w:style>
  <w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360"/></w:pPr></w:style>
  <w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:tblPr><w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="D4DAE3"/><w:left w:val="single" w:sz="4" w:space="0" w:color="D4DAE3"/><w:bottom w:val="single" w:sz="4" w:space="0" w:color="D4DAE3"/><w:right w:val="single" w:sz="4" w:space="0" w:color="D4DAE3"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="D4DAE3"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="D4DAE3"/></w:tblBorders></w:tblPr></w:style>
</w:styles>"""
    with ZipFile(OUTPUT, "w", ZIP_DEFLATED) as docx:
        docx.writestr("[Content_Types].xml", content_types)
        docx.writestr("_rels/.rels", rels)
        docx.writestr("word/_rels/document.xml.rels", doc_rels)
        docx.writestr("word/document.xml", document_xml)
        docx.writestr("word/styles.xml", styles)


if __name__ == "__main__":
    write_docx()
    print(OUTPUT)
