from __future__ import annotations

import re
import subprocess
from pathlib import Path

from app.db.session import SessionLocal
from app.models.student import Student
from app.utils.init_db import init_db

SOURCE_PATH = Path("/Users/karthi/Downloads/Register Numbers 23 Batch.pdf")


def _normalize_phone(value: str) -> str:
    cleaned = re.sub(r"[^\d+]", "", str(value).strip())
    if cleaned in {"", "0"}:
        return ""
    return cleaned


def _extract_pdf_text(source_path: Path) -> str:
    swift_script = f"""
import Foundation
import PDFKit

let url = URL(fileURLWithPath: "{source_path}")
guard let doc = PDFDocument(url: url) else {{
    fputs("failed to open pdf\\n", stderr)
    exit(1)
}}

for index in 0..<doc.pageCount {{
    if let page = doc.page(at: index), let text = page.string {{
        print("=== PAGE \\(index + 1) ===")
        print(text)
    }}
}}
"""
    env = {
        **dict(**subprocess.os.environ),
        "SWIFT_MODULECACHE_PATH": "/tmp/swift-module-cache",
        "CLANG_MODULE_CACHE_PATH": "/tmp/swift-clang-module-cache",
    }
    result = subprocess.run(
        ["swift", "-"],
        input=swift_script,
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    return result.stdout


def _parse_phone_rows(text: str) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}

    for raw_line in text.splitlines():
        line = " ".join(raw_line.split())
        if not re.match(r"^\d+\s+VU", line):
            continue

        tokens = line.split()
        registration_number = next((token for token in tokens if re.fullmatch(r"\d{3}FA\d{5}", token)), None)
        if not registration_number:
            continue

        trailing_phone_tokens: list[str] = []
        for token in reversed(tokens):
            if re.fullmatch(r"[+\d][\d-]*", token):
                trailing_phone_tokens.append(token)
            else:
                break
        trailing_phone_tokens.reverse()

        if len(trailing_phone_tokens) < 2:
            continue

        parent_mobile = _normalize_phone(trailing_phone_tokens[-2])
        student_mobile = _normalize_phone(trailing_phone_tokens[-1])
        records[registration_number] = {
            "parent_mobile": parent_mobile,
            "student_mobile": student_mobile,
        }

    return records


def import_parent_student_phones(source_path: Path = SOURCE_PATH) -> None:
    init_db()
    text = _extract_pdf_text(source_path)
    phone_rows = _parse_phone_rows(text)

    db = SessionLocal()
    try:
        updated = 0
        matched_registration_numbers: list[str] = []

        students = db.query(Student).all()
        for student in students:
            phones = phone_rows.get(student.registration_number)
            if not phones:
                continue

            student.parent_mobile = phones["parent_mobile"]
            student.student_mobile = phones["student_mobile"]
            updated += 1
            matched_registration_numbers.append(student.registration_number)

        db.commit()

        print(f"Parsed phone rows from PDF: {len(phone_rows)}")
        print(f"Updated students with matched registration numbers: {updated}")
        if matched_registration_numbers:
            print("Sample matched registrations:")
            for registration_number in matched_registration_numbers[:20]:
                print(f"- {registration_number}")
    finally:
        db.close()


if __name__ == "__main__":
    import_parent_student_phones()
