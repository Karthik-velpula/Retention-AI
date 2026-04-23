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

SOURCE_PATH = Path("/Users/karthi/Downloads/UP TO 8TH APRIL ATTENDANCE.pdf")


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


def _normalize_name(tokens: list[str]) -> str:
    normalized = " ".join(tokens)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.title()


def _extract_section(text: str) -> str:
    match = re.search(r",\s+(\d+)\s+Section", text)
    return match.group(1) if match else "-"


def _extract_year(text: str) -> int:
    match = re.search(r"III Year", text, re.IGNORECASE)
    if match:
        return 3
    match = re.search(r"II Year", text, re.IGNORECASE)
    if match:
        return 2
    match = re.search(r"IV Year", text, re.IGNORECASE)
    if match:
        return 4
    return 1


def _parse_students(text: str) -> list[dict[str, str]]:
    blocks = list(re.finditer(r"(?m)^(\d+)\s+(23[0-9A-Z]+)\s+", text))
    students: list[dict[str, str]] = []

    for index, match in enumerate(blocks):
        end = blocks[index + 1].start() if index + 1 < len(blocks) else text.find("\n36 ", match.start())
        if end == -1:
            end = len(text)
        block = text[match.start():end]
        compact = re.sub(r"\s+", " ", block).strip()
        parts = compact.split()
        if len(parts) < 3:
            continue

        serial_number, registration_number, *rest = parts
        if not serial_number.isdigit():
            continue

        name_tokens: list[str] = []
        for token in rest:
            if re.match(r"^-?$", token) or re.match(r"^\d+\(\d+\.\d+%\)$", token) or re.match(r"^\d+\.\d+$", token):
                break
            name_tokens.append(token)

        if not name_tokens:
            continue

        students.append(
            {
                "registration_number": registration_number,
                "name": _normalize_name(name_tokens),
            }
        )

    return students


def import_students_from_attendance_roster_pdf(source_path: Path = SOURCE_PATH) -> None:
    _ensure_schema()
    text = _extract_pdf_text(source_path)
    section = _extract_section(text)
    year = _extract_year(text)
    parsed_students = _parse_students(text)

    db = SessionLocal()
    try:
        inserted = 0
        updated = 0
        for row in parsed_students:
            registration_number = row["registration_number"]
            student = db.query(Student).filter(Student.registration_number == registration_number).first()

            if student:
                student.name = row["name"]
                if student.section in {"", "-"}:
                    student.section = section
                if not student.year:
                    student.year = year
                if student.department in {"", "-", None}:
                    student.department = "CSE"
                updated += 1
                continue

            student = Student(
                registration_number=registration_number,
                name=row["name"],
                email=f"{registration_number.lower()}@gmail.com",
                counselor_name="-",
                codechef_username="-",
                codechef_contests_participated=0,
                codechef_problems_solved=0,
                codechef_participation_status="Not Available",
                section=section,
                gender="-",
                age=None,
                gpa=0.0,
                attendance=0.0,
                marks=0.0,
                department="CSE",
                year=year,
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
        print(f"Section={section}, Year={year}")
    finally:
        db.close()


if __name__ == "__main__":
    cli_source_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else SOURCE_PATH
    import_students_from_attendance_roster_pdf(cli_source_path)
