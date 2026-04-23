from app.db.session import SessionLocal
from app.models.student import Student
from app.services.student_service import normalize_student_email


def fix_student_emails() -> None:
    db = SessionLocal()
    try:
        students = db.query(Student).all()
        updated = 0
        for student in students:
            normalized = normalize_student_email(student.email)
            if normalized != student.email:
                student.email = normalized
                updated += 1
        db.commit()
        print(f"Updated {updated} student email(s).")
    finally:
        db.close()


if __name__ == "__main__":
    fix_student_emails()
