from app.db.session import SessionLocal
from app.models.student import Student


def assign_registration_numbers() -> None:
    db = SessionLocal()
    try:
        students = db.query(Student).order_by(Student.id.asc()).all()
        start = 4001
        updated = 0
        for index, student in enumerate(students):
            reg_no = f"231FA0{start + index:04d}"
            if student.registration_number != reg_no:
                student.registration_number = reg_no
                updated += 1
        db.commit()
        print(f"Updated {updated} registration number(s).")
    finally:
        db.close()


if __name__ == "__main__":
    assign_registration_numbers()
