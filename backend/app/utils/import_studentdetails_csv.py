from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from email_validator import EmailNotValidError, validate_email
from sqlalchemy import inspect, text

from app.models.financial import Financial
from app.models.lms_activity import LMSActivity
from app.models.student import Student
from app.db.session import Base, SessionLocal, engine

SOURCE_PATH = Path("/Users/karthi/Downloads/studentdetails.csv")


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


def _normalize_email(raw_email: str, registration_number: str) -> str:
    value = str(raw_email).strip().lower().replace(" ", "")
    if not value or value in {"-", "0", "nan"}:
        return f"{registration_number.lower()}@gmail.com"
    try:
        return validate_email(value, check_deliverability=False).normalized
    except EmailNotValidError:
        return f"{registration_number.lower()}@gmail.com"


def _load_students(source_path: Path) -> pd.DataFrame:
    df = pd.read_csv(source_path)
    df.columns = [str(column).strip().lower() for column in df.columns]
    df = df.rename(
        columns={
            "registerno": "registration_number",
            "sectioncode": "section",
            "counsellor_name": "counselor_name",
            "cgpa": "gpa",
        }
    )
    required = {"registration_number", "name", "email", "year", "gpa"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    df = df.dropna(subset=["registration_number", "name"])
    df["registration_number"] = df["registration_number"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip().str.title()
    df["email"] = [
        _normalize_email(email, registration_number)
        for email, registration_number in zip(df["email"], df["registration_number"], strict=False)
    ]
    counselor_series = df["counselor_name"] if "counselor_name" in df.columns else pd.Series("-", index=df.index)
    section_series = df["section"] if "section" in df.columns else pd.Series("-", index=df.index)
    gender_series = df["gender"] if "gender" in df.columns else pd.Series("-", index=df.index)
    age_series = df["age"] if "age" in df.columns else pd.Series(None, index=df.index)

    df["counselor_name"] = counselor_series.fillna("-").astype(str).str.strip().replace({"": "-", "nan": "-"})
    df["section"] = section_series.fillna("-").astype(str).str.strip().replace({"": "-", "nan": "-"})
    df["gender"] = gender_series.fillna("-").astype(str).str.strip().str.upper().replace({"": "-", "nan": "-"})
    df["age"] = pd.to_numeric(age_series, errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(1).astype(int)
    df["gpa"] = pd.to_numeric(df["gpa"], errors="coerce").fillna(0.0)
    return df


def import_studentdetails_csv(source_path: Path = SOURCE_PATH) -> None:
    _ensure_schema()
    df = _load_students(source_path)

    db = SessionLocal()
    try:
        inserted = 0
        updated = 0

        for row in df.to_dict(orient="records"):
            student = db.query(Student).filter(Student.registration_number == row["registration_number"]).first()
            dataset_email = row["email"]

            if student:
                student.name = row["name"]
                student.email = dataset_email
                student.section = row["section"]
                student.gender = row["gender"]
                student.age = int(row["age"]) if pd.notna(row["age"]) else None
                student.gpa = float(row["gpa"])
                student.counselor_name = row["counselor_name"]
                student.codechef_username = getattr(student, "codechef_username", "-") or "-"
                student.codechef_contests_participated = getattr(student, "codechef_contests_participated", 0) or 0
                student.codechef_problems_solved = getattr(student, "codechef_problems_solved", 0) or 0
                student.codechef_participation_status = getattr(student, "codechef_participation_status", "Not Available") or "Not Available"
                student.attendance = 0.0
                student.marks = 0.0
                student.department = "-"
                student.year = int(row["year"])
                student.career_interest = "-"
                student.skills = "-"
                updated += 1
            else:
                student = Student(
                    registration_number=row["registration_number"],
                    name=row["name"],
                    email=dataset_email,
                    counselor_name=row["counselor_name"],
                    codechef_username="-",
                    codechef_contests_participated=0,
                    codechef_problems_solved=0,
                    codechef_participation_status="Not Available",
                    section=row["section"],
                    gender=row["gender"],
                    age=int(row["age"]) if pd.notna(row["age"]) else None,
                    gpa=float(row["gpa"]),
                    attendance=0.0,
                    marks=0.0,
                    department="-",
                    year=int(row["year"]),
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
                    fee_due=0,
                    payment_delay_days=0,
                    scholarship_amount=0,
                )
                db.add(student)
                inserted += 1

        db.commit()
        print(f"Imported {inserted} students and updated {updated} students from {source_path}.")
        print("Missing text fields were stored as '-'. Required numeric fields without source data were stored as 0.")
        print("Missing or invalid emails were stored as '<registration_number>@gmail.com'. Dataset emails are otherwise kept as provided.")
    finally:
        db.close()


if __name__ == "__main__":
    cli_source_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else SOURCE_PATH
    import_studentdetails_csv(cli_source_path)
