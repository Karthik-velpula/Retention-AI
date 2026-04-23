from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.models.student import Student
from app.models.subject_attendance import SubjectAttendance

SOURCE_PATH = Path("/Users/karthi/Downloads/ATT-%.pdf")

SUBJECT_COLUMNS = [
    "22CE852 EE",
    "22CE855 SE",
    "22CS305 IIC",
    "22CS307 SE",
    "22CS308 IDP-II",
    "22CS311 PADCOM",
    "22CS407 CNS",
    "22CS808 MAD",
    "22CS958 CLSA",
    "22CT851 BRTEP",
    "22CT853 CDL",
    "22EC856 IT",
    "22EE855 FEV",
    "22FT853 BVT",
    "22MS851 MHRM",
    "22MT855 FM",
    "22MT861 OT-OE",
    "22TP302 QALR",
    "22TP851 ESDOI",
    "22TP852 MIH&IC",
    "22TT854 TTXT",
    "24RA853 AHR",
    "LIB001 library",
    "OC223 Counseling",
    "TRG001 TRg",
]


def _extract_pdf_text(path: Path) -> str:
    swift_script = f"""
import Foundation
import PDFKit

let url = URL(fileURLWithPath: "{path}")
if let document = PDFDocument(url: url) {{
    var text = ""
    for index in 0..<document.pageCount {{
        text += (document.page(at: index)?.string ?? "") + "\\n"
    }}
    print(text)
}} else {{
    fputs("PDF_OPEN_FAILED\\n", stderr)
    exit(1)
}}
"""
    env = {"CLANG_MODULE_CACHE_PATH": "/tmp/clang-module-cache"}
    completed = subprocess.run(
        ["swift", "-"],
        input=swift_script,
        text=True,
        capture_output=True,
        env={**env, **os.environ},
        check=True,
    )
    return completed.stdout


def _extract_student_blocks(text: str) -> list[str]:
    if "No. Of Conducted Hours->" not in text:
        raise ValueError("Could not locate attendance rows in the PDF.")

    table_text = text.split("No. Of Conducted Hours->", 1)[1]
    table_text = table_text.split("\nPrint", 1)[0]
    matches = list(re.finditer(r"(?m)^(\d+)\s+(23[0-9A-Z]+)\s+", table_text))

    blocks: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(table_text)
        blocks.append(table_text[start:end])
    return blocks


def _parse_student_attendance(text: str, subjects: list[str]) -> list[dict[str, object]]:
    parsed_rows: list[dict[str, object]] = []

    for block in _extract_student_blocks(text):
        compact = re.sub(r"\s+", " ", block).strip()
        parts = compact.split(maxsplit=2)
        if len(parts) < 3:
            continue

        registration_number = parts[1]
        values = re.findall(r"\d+\.\d+%|-", compact)
        overall_match = re.search(r"(\d+\.\d+)\s*$", compact)

        if len(values) != len(subjects):
            raise ValueError(
                f"Expected {len(subjects)} subject entries for {registration_number}, found {len(values)}."
            )
        if overall_match is None:
            raise ValueError(f"Could not find overall attendance for {registration_number}.")

        subject_rows: list[tuple[str, float]] = []
        for subject_name, raw_value in zip(subjects, values, strict=False):
            if raw_value == "-":
                continue
            subject_rows.append((subject_name, float(raw_value.rstrip("%"))))

        parsed_rows.append(
            {
                "registration_number": registration_number,
                "overall_attendance": float(overall_match.group(1)),
                "subject_rows": subject_rows,
            }
        )

    return parsed_rows


def import_subject_attendance_from_pdf(source_path: Path = SOURCE_PATH) -> None:
    text = _extract_pdf_text(source_path)
    subjects = SUBJECT_COLUMNS
    parsed_rows = _parse_student_attendance(text, subjects)

    if not parsed_rows:
        raise ValueError("No student attendance rows were extracted from the attendance PDF.")

    db = SessionLocal()
    try:
        updated = 0

        for row in parsed_rows:
            student = (
                db.query(Student)
                .filter(Student.registration_number == row["registration_number"])
                .first()
            )
            if not student:
                continue

            db.query(SubjectAttendance).filter(SubjectAttendance.student_id == student.id).delete(
                synchronize_session=False
            )

            subject_rows = row["subject_rows"]
            for subject_name, attendance_percentage in subject_rows:
                db.add(
                    SubjectAttendance(
                        student_id=student.id,
                        subject_name=subject_name,
                        attendance_percentage=attendance_percentage,
                    )
                )

            student.attendance = float(row["overall_attendance"])
            updated += 1

        db.commit()
        print(
            f"Stored subject-wise attendance for {updated} students from {source_path.name}."
        )
        print("Subjects:", ", ".join(subjects))
    finally:
        db.close()


if __name__ == "__main__":
    cli_source_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else SOURCE_PATH
    import_subject_attendance_from_pdf(cli_source_path)
