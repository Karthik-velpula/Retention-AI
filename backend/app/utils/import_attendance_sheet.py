from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import inspect, text

from app.db.base import Financial, LMSActivity, Prediction, Student, SubjectAttendance
from app.db.session import Base, SessionLocal, engine

SOURCE_PATH = Path("/Users/karthi/Downloads/III B.Tech Tentative Attendance (2).xls")


def _ensure_schema() -> None:
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    student_columns = {column["name"] for column in inspector.get_columns("students")}
    with engine.begin() as conn:
        if "counselor_name" not in student_columns:
            conn.execute(text("ALTER TABLE students ADD COLUMN counselor_name VARCHAR(120) NOT NULL DEFAULT ''"))


def _read_sheet() -> pd.DataFrame:
    raw = pd.read_excel(SOURCE_PATH, header=5)
    raw.columns = [str(col).strip() for col in raw.columns]
    df = raw.rename(
        columns={
            "Register No": "registration_number",
            "Name": "name",
            "Counselore Name": "counselor_name",
            "Section": "section",
            "Subject Name": "subject_name",
            "Att%": "attendance_percentage",
        }
    )
    df = df[["registration_number", "name", "counselor_name", "section", "subject_name", "attendance_percentage"]].copy()
    df = df.dropna(subset=["registration_number", "subject_name"])
    df["registration_number"] = df["registration_number"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip().str.title()
    df["counselor_name"] = df["counselor_name"].fillna("").astype(str).str.strip()
    df["subject_name"] = df["subject_name"].astype(str).str.strip()
    df["attendance_percentage"] = pd.to_numeric(df["attendance_percentage"], errors="coerce").fillna(0)
    return df


def _neutral_metric(attendance: float) -> tuple[float, float, int, float, float, int]:
    gpa = round(max(4.5, min(9.5, 4.5 + attendance / 20)), 2)
    marks = round(max(40, min(95, attendance)), 2)
    weekly_logins = max(2, int(round(attendance / 8)))
    avg_time_spent = round(max(1.5, min(8.0, attendance / 15)), 2)
    assignment_submission_rate = round(max(45, min(95, attendance)), 2)
    missed_assignments = max(0, int(round((100 - attendance) / 10)))
    return gpa, marks, weekly_logins, avg_time_spent, assignment_submission_rate, missed_assignments


def import_attendance_sheet() -> None:
    _ensure_schema()
    df = _read_sheet()
    grouped = df.groupby("registration_number", sort=True)

    db = SessionLocal()
    try:
        db.query(SubjectAttendance).delete()
        db.execute(text("DELETE FROM predictions"))
        db.execute(text("DELETE FROM lms_activity"))
        db.execute(text("DELETE FROM financial"))
        db.execute(text("DELETE FROM students"))
        db.commit()

        inserted = 0
        for registration_number, group in grouped:
            first = group.iloc[0]
            overall_attendance = round(float(group["attendance_percentage"].mean()), 2)
            gpa, marks, weekly_logins, avg_time_spent, submission_rate, missed_assignments = _neutral_metric(
                overall_attendance
            )
            student = Student(
                registration_number=registration_number,
                name=first["name"],
                email=f"{registration_number.lower()}@gmail.com",
                counselor_name=first["counselor_name"],
                gpa=gpa,
                attendance=overall_attendance,
                marks=marks,
                department="CSE",
                year=3,
                career_interest="Software Engineering",
                skills="Python,Data Structures",
            )
            student.lms_activity = LMSActivity(
                weekly_logins=weekly_logins,
                avg_time_spent=avg_time_spent,
                assignment_submission_rate=submission_rate,
                missed_assignments=missed_assignments,
            )
            student.financial = Financial(
                fee_due=0,
                payment_delay_days=0,
                scholarship_amount=0,
            )
            student.subject_attendance = [
                SubjectAttendance(
                    subject_name=row["subject_name"],
                    attendance_percentage=float(row["attendance_percentage"]),
                )
                for _, row in group.drop_duplicates(subset=["subject_name"]).iterrows()
            ]
            db.add(student)
            inserted += 1

        db.commit()
        print(f"Imported {inserted} unique students from {SOURCE_PATH}.")
    finally:
        db.close()


if __name__ == "__main__":
    import_attendance_sheet()
