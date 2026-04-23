from __future__ import annotations

import random
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from app.core.faculty_assignments import faculty_name_for_position
from app.db.session import SessionLocal
from app.models.financial import Financial
from app.models.lms_activity import LMSActivity
from app.models.student import Student
from app.models.subject_attendance import SubjectAttendance

SOURCE_PATH = Path("/Users/karthi/Downloads/CSE Credit Status as on 07-08-2025.xlsx")


def _read_sheet() -> pd.DataFrame:
    raw = pd.read_excel(SOURCE_PATH, header=6, sheet_name="CSE")
    raw.columns = [str(col).strip() for col in raw.columns]
    df = raw.rename(columns={"Register No": "registration_number", "Name": "name"})
    df = df[["registration_number", "name"]].dropna().copy()
    df["registration_number"] = df["registration_number"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip().str.title()
    df = df.drop_duplicates(subset=["registration_number"])
    return df


def _random_student_profile(seed_key: str) -> dict[str, float | int | str]:
    rng = random.Random(seed_key)
    cgpa = round(rng.uniform(5.2, 9.7), 2)
    attendance = round(rng.uniform(58, 95), 1)
    fees_paid_status = rng.choice(["Paid", "Not Paid"])
    fee_due = 0 if fees_paid_status == "Paid" else round(rng.uniform(5000, 18000), 2)
    payment_delay_days = 0 if fees_paid_status == "Paid" else rng.randint(5, 30)
    weekly_logins = rng.randint(5, 20)
    avg_time_spent = round(rng.uniform(2.5, 8.5), 2)
    submission_rate = round(rng.uniform(55, 95), 2)
    missed_assignments = rng.randint(0, 5)
    return {
        "cgpa": cgpa,
        "attendance": attendance,
        "marks": round(min(95, max(50, cgpa * 10)), 2),
        "fees_paid_status": fees_paid_status,
        "fee_due": fee_due,
        "payment_delay_days": payment_delay_days,
        "weekly_logins": weekly_logins,
        "avg_time_spent": avg_time_spent,
        "assignment_submission_rate": submission_rate,
        "missed_assignments": missed_assignments,
    }


def import_credit_status_sheet() -> None:
    df = _read_sheet()
    db = SessionLocal()
    try:
        db.query(SubjectAttendance).delete()
        db.execute(text("DELETE FROM predictions"))
        db.execute(text("DELETE FROM lms_activity"))
        db.execute(text("DELETE FROM financial"))
        db.execute(text("DELETE FROM students"))
        db.commit()

        inserted = 0
        for index, (_, row) in enumerate(df.iterrows()):
            profile = _random_student_profile(row["registration_number"])
            student = Student(
                registration_number=row["registration_number"],
                name=row["name"],
                email=f"{row['registration_number'].lower()}@gmail.com",
                counselor_name=faculty_name_for_position(index),
                gpa=float(profile["cgpa"]),
                attendance=float(profile["attendance"]),
                marks=float(profile["marks"]),
                department="CSE",
                year=3,
                career_interest="Software Engineering",
                skills="Python,Data Structures",
            )
            student.lms_activity = LMSActivity(
                weekly_logins=int(profile["weekly_logins"]),
                avg_time_spent=float(profile["avg_time_spent"]),
                assignment_submission_rate=float(profile["assignment_submission_rate"]),
                missed_assignments=int(profile["missed_assignments"]),
            )
            student.financial = Financial(
                fee_due=float(profile["fee_due"]),
                payment_delay_days=int(profile["payment_delay_days"]),
                scholarship_amount=0,
            )
            db.add(student)
            inserted += 1

        db.commit()
        print(f"Imported {inserted} unique students from {SOURCE_PATH}.")
    finally:
        db.close()


if __name__ == "__main__":
    import_credit_status_sheet()
