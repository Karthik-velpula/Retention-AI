from __future__ import annotations

import re
import sys
from pathlib import Path

from sqlalchemy import inspect, text

from app.db.session import Base, SessionLocal, engine
from app.models.financial import Financial
from app.models.lms_activity import LMSActivity
from app.models.student import Student
from app.utils.import_subject_attendance_pdf import _extract_pdf_text

SOURCE_PATH = Path("/Users/karthi/Downloads/ATT-% (1).pdf")


def _ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    student_columns = {column["name"] for column in inspector.get_columns("students")}
    with engine.begin() as connection:
        if "section" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN section VARCHAR(20) NOT NULL DEFAULT '-'"))
        if "gender" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN gender VARCHAR(20) NOT NULL DEFAULT '-'"))
        if "age" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN age INTEGER NULL"))
        if "codechef_username" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN codechef_username VARCHAR(100) NOT NULL DEFAULT '-'"))
        if "codechef_contests_participated" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN codechef_contests_participated INTEGER NOT NULL DEFAULT 0"))
        if "codechef_problems_solved" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN codechef_problems_solved INTEGER NOT NULL DEFAULT 0"))
        if "codechef_participation_status" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN codechef_participation_status VARCHAR(30) NOT NULL DEFAULT 'Not Available'"))
        if "codechef_last_synced_at" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN codechef_last_synced_at DATETIME NULL"))
    student_indexes = {index["name"]: index for index in inspector.get_indexes("students")}
    with engine.begin() as connection:
        email_index = student_indexes.get("ix_students_email")
        if email_index and email_index.get("unique"):
            connection.execute(text("DROP INDEX ix_students_email ON students"))
            connection.execute(text("CREATE INDEX ix_students_email ON students (email)"))


def _normalize_name(tokens: list[str]) -> str:
    normalized = " ".join(tokens)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = normalized.rstrip("-").strip()
    return normalized.title()


def _parse_students(text: str) -> list[dict[str, str | float]]:
    matches = list(re.finditer(r"(?m)^(\d+)\s+(23[0-9A-Z]+)\s+", text))
    students: list[dict[str, str | float]] = []

    for index, match in enumerate(matches):
        block_end = matches[index + 1].start() if index + 1 < len(matches) else text.find("\nPrint", match.start())
        if block_end == -1:
            block_end = len(text)
        block = text[match.start():block_end]
        compact = re.sub(r"\s+", " ", block).strip()
        parts = compact.split()

        if len(parts) < 3:
            continue

        serial_number, registration_number, *rest = parts
        if not serial_number.isdigit():
            continue

        name_tokens: list[str] = []
        for token in rest:
            if token == "-" or any(char.isdigit() for char in token):
                break
            name_tokens.append(token)

        if not name_tokens:
            continue

        attendance_matches = re.findall(r"(\d+\.\d+)(?=%)", compact)
        overall_attendance = float(attendance_matches[-1]) if attendance_matches else 0.0

        students.append(
            {
                "registration_number": registration_number,
                "name": _normalize_name(name_tokens),
                "attendance": overall_attendance,
            }
        )

    return students


def import_students_from_attendance_pdf(source_path: Path = SOURCE_PATH) -> None:
    _ensure_schema()
    text = _extract_pdf_text(source_path)
    parsed_students = _parse_students(text)

    if not parsed_students:
        raise ValueError(f"No student rows were found in {source_path}.")

    db = SessionLocal()
    try:
        inserted = 0
        updated = 0

        for row in parsed_students:
            registration_number = str(row["registration_number"])
            student = db.query(Student).filter(Student.registration_number == registration_number).first()

            if student:
                student.name = str(row["name"])
                student.email = student.email or f"{registration_number.lower()}@gmail.com"
                student.attendance = float(row["attendance"])
                student.section = student.section or "15"
                student.department = student.department or "CSE"
                student.year = student.year or 3
                student.counselor_name = student.counselor_name or "-"
                updated += 1
                continue

            student = Student(
                registration_number=registration_number,
                name=str(row["name"]),
                email=f"{registration_number.lower()}@gmail.com",
                counselor_name="-",
                codechef_username="-",
                codechef_contests_participated=0,
                codechef_problems_solved=0,
                codechef_participation_status="Not Available",
                section="15",
                gender="-",
                age=None,
                gpa=0.0,
                attendance=float(row["attendance"]),
                marks=0.0,
                department="CSE",
                year=3,
                career_interest="-",
                skills="-",
            )
            student.lms_activity = LMSActivity(
                weekly_logins=0,
                avg_time_spent=0.0,
                assignment_submission_rate=0.0,
                missed_assignments=0,
            )
            student.financial = Financial(
                fee_due=0.0,
                payment_delay_days=0,
                scholarship_amount=0.0,
            )
            db.add(student)
            inserted += 1

        db.commit()
        print(f"Imported {inserted} students and updated {updated} students from {source_path.name}.")
    finally:
        db.close()


if __name__ == "__main__":
    cli_source_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else SOURCE_PATH
    import_students_from_attendance_pdf(cli_source_path)
