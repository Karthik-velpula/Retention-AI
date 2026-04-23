from app.db.session import SessionLocal
from app.models.student import Student
from app.models.subject_attendance import SubjectAttendance
from app.utils.init_db import init_db


SUBJECT_NAME = "22CS958 CLSA"


def backfill_clsa_subject_rows() -> dict[str, int]:
    init_db()
    db = SessionLocal()
    try:
        added_rows = 0
        students = db.query(Student).all()

        for student in students:
            existing = (
                db.query(SubjectAttendance.id)
                .filter(
                    SubjectAttendance.student_id == student.id,
                    SubjectAttendance.subject_name == SUBJECT_NAME,
                )
                .first()
            )
            if existing:
                continue

            db.add(
                SubjectAttendance(
                    student_id=student.id,
                    subject_name=SUBJECT_NAME,
                    attendance_percentage=0,
                )
            )
            added_rows += 1

        db.commit()
        return {"added_subject_rows": added_rows}
    finally:
        db.close()


if __name__ == "__main__":
    summary = backfill_clsa_subject_rows()
    print(f"Added {summary['added_subject_rows']} missing CLSA subject rows.")
