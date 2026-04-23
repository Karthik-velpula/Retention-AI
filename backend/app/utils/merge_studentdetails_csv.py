from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from email_validator import EmailNotValidError, validate_email

from app.db.session import SessionLocal
from app.models.student import Student

SOURCE_PATH = Path("/Users/karthi/Downloads/studentdetails1.csv")


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
    df = df.dropna(subset=["registration_number", "name"])
    df["registration_number"] = df["registration_number"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip().str.title()
    df["email"] = [
        _normalize_email(email, registration_number)
        for email, registration_number in zip(df["email"], df["registration_number"], strict=False)
    ]
    df["counselor_name"] = df["counselor_name"].fillna("-").astype(str).str.strip().replace({"": "-", "nan": "-"})
    df["section"] = df["section"].fillna("-").astype(str).str.strip().replace({"": "-", "nan": "-"})
    df["gender"] = df["gender"].fillna("-").astype(str).str.strip().str.upper().replace({"": "-", "nan": "-"})
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(1).astype(int)
    df["gpa"] = pd.to_numeric(df["gpa"], errors="coerce").fillna(0.0)
    return df


def merge_studentdetails_csv(source_path: Path = SOURCE_PATH) -> None:
    df = _load_students(source_path)
    lookup = {
        row["registration_number"]: row
        for row in df.to_dict(orient="records")
    }

    db = SessionLocal()
    try:
        matched = 0
        missing = 0

        for student in db.query(Student).all():
            row = lookup.get(student.registration_number)
            if row is None:
                missing += 1
                continue

            student.name = row["name"]
            student.email = row["email"]
            student.section = row["section"]
            student.gender = row["gender"]
            student.age = int(row["age"]) if pd.notna(row["age"]) else None
            student.year = int(row["year"])
            student.gpa = float(row["gpa"])
            student.counselor_name = row["counselor_name"]
            student.department = "CSE"
            matched += 1

        db.commit()
        print(f"Merged CSV details into {matched} existing students from {source_path.name}.")
        print(f"No CSV row was found for {missing} existing students.")
    finally:
        db.close()


if __name__ == "__main__":
    cli_source_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else SOURCE_PATH
    merge_studentdetails_csv(cli_source_path)
