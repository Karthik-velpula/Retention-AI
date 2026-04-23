from __future__ import annotations

import re
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.models.student import Student
from app.models.subject_attendance import SubjectAttendance
from app.utils.import_subject_attendance_pdf import _extract_pdf_text

SOURCE_PATH = Path("/Users/karthi/Downloads/UP TO 8TH APRIL ATTENDANCE.pdf")

SUBJECT_COLUMNS = [
    "SE",
    "PADCOM",
    "CNS",
    "CLSA",
    "EBI-L",
    "IIC",
    "SE Lab",
    "CNS-L",
    "MAD Lab",
    "IT Lab",
    "BVT-L",
    "QALR",
    "MAD",
    "EBI",
    "EE",
    "SE (Elective)",
    "BRTEP",
    "CDL",
    "IT",
    "FEV",
    "BVT",
    "FM",
    "OT-OE",
    "TFT",
    "ESDOI",
    "MIH&IC",
    "TTXT",
    "AHR",
    "IDP-II",
    "library",
    "Counseling",
    "TRg",
]


def _extract_student_blocks(text: str) -> list[str]:
    text = text.split("\nPrint", 1)[0]
    matches = list(re.finditer(r"(?m)^(\d+)\s+(23[0-9A-Z]+)\s+", text))
    blocks: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks.append(text[start:end])
    return blocks


def _parse_student_attendance(text: str) -> list[dict[str, object]]:
    parsed_rows: list[dict[str, object]] = []
    for block in _extract_student_blocks(text):
        compact = re.sub(r"\s+", " ", block).strip()
        parts = compact.split(maxsplit=2)
        if len(parts) < 3:
            continue

        registration_number = parts[1]
        values = re.findall(r"\d+\(\d+\.\d+%\)|-", compact)
        overall_match = re.search(r"(\d+\.\d+)\s*$", compact)

        if len(values) != len(SUBJECT_COLUMNS):
            raise ValueError(
                f"Expected {len(SUBJECT_COLUMNS)} subject entries for {registration_number}, found {len(values)}."
            )
        if overall_match is None:
            raise ValueError(f"Could not find overall attendance for {registration_number}.")

        subject_rows: list[tuple[str, float]] = []
        for subject_name, raw_value in zip(SUBJECT_COLUMNS, values, strict=False):
            if raw_value == "-":
                continue
            percentage_match = re.search(r"\((\d+\.\d+)%\)", raw_value)
            if percentage_match is None:
                continue
            subject_rows.append((subject_name, float(percentage_match.group(1))))

        parsed_rows.append(
            {
                "registration_number": registration_number,
                "overall_attendance": float(overall_match.group(1)),
                "subject_rows": subject_rows,
            }
        )

    return parsed_rows


def import_subject_attendance_roster_pdf(source_path: Path = SOURCE_PATH) -> None:
    text = _extract_pdf_text(source_path)
    parsed_rows = _parse_student_attendance(text)

    if not parsed_rows:
        raise ValueError(f"No student attendance rows were extracted from {source_path.name}.")

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

            for subject_name, attendance_percentage in row["subject_rows"]:
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
    finally:
        db.close()


if __name__ == "__main__":
    cli_source_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else SOURCE_PATH
    import_subject_attendance_roster_pdf(cli_source_path)
