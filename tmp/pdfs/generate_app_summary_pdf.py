from __future__ import annotations

from pathlib import Path


PAGE_WIDTH = 612
PAGE_HEIGHT = 792
LEFT = 44
RIGHT = 568
TOP = 748
BOTTOM = 44


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


class PdfPage:
    def __init__(self) -> None:
        self.commands: list[str] = []
        self.y = TOP

    def text(self, x: int, y: int, text: str, font: str = "F1", size: int = 11) -> None:
        safe = escape_pdf_text(text)
        self.commands.append(f"BT /{font} {size} Tf 1 0 0 1 {x} {y} Tm ({safe}) Tj ET")

    def heading(self, text: str) -> None:
        self.text(LEFT, self.y, text, font="F2", size=15)
        self.y -= 18

    def paragraph(self, text: str, size: int = 10, leading: int = 12, max_chars: int = 88) -> None:
        for line in wrap_text(text, max_chars):
            self.text(LEFT, self.y, line, size=size)
            self.y -= leading
        self.y -= 4

    def bullet_lines(self, items: list[str], size: int = 10, leading: int = 12) -> None:
        for item in items:
            lines = wrap_text(item, 82)
            if not lines:
                continue
            self.text(LEFT + 2, self.y, "-", font="F2", size=size)
            self.text(LEFT + 12, self.y, lines[0], size=size)
            self.y -= leading
            for line in lines[1:]:
                self.text(LEFT + 12, self.y, line, size=size)
                self.y -= leading
        self.y -= 4

    def divider(self) -> None:
        self.commands.append(f"{LEFT} {self.y} m {RIGHT} {self.y} l S")
        self.y -= 12

    def finish(self) -> str:
        return "\n".join(
            [
                "q",
                "0.2 w",
                "0.15 0.22 0.35 RG",
                f"{LEFT} 764 m {RIGHT} 764 l S",
                "Q",
                *self.commands,
            ]
        )


def build_pdf(content_stream: str) -> bytes:
    objects: list[bytes] = []

    def add_object(data: str) -> int:
        objects.append(data.encode("latin-1"))
        return len(objects)

    catalog_id = add_object("<< /Type /Catalog /Pages 2 0 R >>")
    pages_id = add_object("<< /Type /Pages /Count 1 /Kids [3 0 R] >>")
    page_id = add_object(
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        "/Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>"
    )
    content_id = add_object(f"<< /Length {len(content_stream.encode('latin-1'))} >>\nstream\n{content_stream}\nendstream")
    font1_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font2_id = add_object("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    assert [catalog_id, pages_id, page_id, content_id, font1_id, font2_id] == [1, 2, 3, 4, 5, 6]

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for idx, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode("latin-1"))
        out.extend(obj)
        out.extend(b"\nendobj\n")

    xref_start = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))

    out.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_start}\n"
            "%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(out)


def main() -> None:
    page = PdfPage()
    page.text(LEFT, 772, "App Summary: Underwriting Tool Backend", font="F2", size=20)
    page.text(LEFT, 754, "Repo-based one-page overview", size=10)

    page.heading("What It Is")
    page.paragraph(
        "A FastAPI backend for onboarding users and processing bank statement analysis workflows. "
        "It accepts PDF statement uploads, sends them to ScoreMe for analysis, stores workflow state in MongoDB, "
        "links accounts in PostgreSQL, and ingests returned reports."
    )

    page.heading("Who It Is For")
    page.paragraph(
        "Primary persona: a business customer or loan applicant using an underwriting portal to register, log in, "
        "and upload bank statements for review. Internal underwriting or ops teams likely consume the resulting data, "
        "but that user flow is not found in repo."
    )

    page.heading("What It Does")
    page.bullet_lines(
        [
            "Registers users, creates linked account records, and emails login credentials.",
            "Authenticates users with JWT stored in an HTTP-only cookie.",
            "Returns the current authenticated user profile.",
            "Accepts up to 12 PDF bank statements plus account metadata per upload request.",
            "Submits uploads to the ScoreMe bank statement analysis API.",
            "Stores upload metadata and original PDFs in Google Cloud Storage and MongoDB.",
            "Consumes webhook/report URLs, updates reference records, and saves normalized bank report data.",
        ]
    )

    page.heading("How It Works")
    page.bullet_lines(
        [
            "Client -> FastAPI routes (`/v1/auth`, `/v1/user`, `/v1/bsa`) with auth middleware on non-public paths.",
            "FastAPI lifespan opens MongoDB and PostgreSQL connections and stores them on `app.state`.",
            "Auth flow writes user/auth documents to MongoDB and may create/find an `accounts` row in PostgreSQL.",
            "BSA upload flow validates PDFs and metadata, sends files to ScoreMe, and stores a `bsa_reference` record in MongoDB.",
            "Background task uploads source PDFs to Google Cloud Storage and stores file metadata in `bsa_file_uploads`.",
            "Webhook endpoint updates the reference record, then fetches the ScoreMe JSON report and stores an optimized document in `bankstatementreport`.",
            "Celery app exists with Redis config and `tasks.bsa_tasks` import, but active worker startup usage is not found in repo.",
        ]
    )

    page.heading("How To Run")
    page.bullet_lines(
        [
            "Create and activate a Python virtual environment.",
            "Install dependencies: `pip install -r requirements.txt`.",
            "Set required environment variables seen in code: `MONGO_URI`, `POSTGRES_URI`, `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `CLIENT_ID`, `CLIENT_SECRET`, `GCS_BUCKET_NAME`, `APP_PASSWORD`, `ACCOUNT_OWNER_ID`, and `CREATED_BY_ID`.",
            "Provide Google Cloud credentials for the storage client. Exact setup method: Not found in repo.",
            "Start the API with `python main.py` and it serves on port 8080.",
            "Optional infra implied by code: MongoDB, PostgreSQL, ScoreMe access, SMTP, and likely Redis/Celery; exact local bootstrap commands are Not found in repo.",
        ]
    )

    page.text(LEFT, BOTTOM, "Evidence sources: main.py, routes/*, controller/*, services/scoreme_service.py, tasks/bsa_tasks.py,", size=8)
    page.text(LEFT, BOTTOM - 10, "database/*, middleware/authorization_middleware.py, requirements.txt, migrations/001_initial_indexes.py", size=8)

    output_dir = Path("output/pdf")
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "underwriting_tool_backend_summary.pdf"
    pdf_path.write_bytes(build_pdf(page.finish()))
    print(pdf_path.resolve())


if __name__ == "__main__":
    main()
