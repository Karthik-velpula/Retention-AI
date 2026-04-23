from __future__ import annotations

import json
import secrets

from app.core.faculty_assignments import (
    FACULTY_NAMES,
    FACULTY_PASSWORD,
    active_counselor_names,
    build_faculty_login_ids,
    faculty_email,
)
from app.core.security import generate_security_grid, get_password_hash, is_legacy_shared_grid
from app.db.session import SessionLocal
from app.models.student import Student
from app.models.user import User


def sync_faculty_assignments() -> None:
    db = SessionLocal()
    try:
        counselor_names = active_counselor_names(FACULTY_NAMES)
        canonical_names = {name.casefold(): name for name in counselor_names}
        active_emails = {faculty_email(name) for name in counselor_names}
        student_assignments = db.query(
            Student.year,
            Student.section,
            Student.counselor_name,
            Student.registration_number,
        ).all()
        faculty_login_ids = build_faculty_login_ids(student_assignments, counselor_names)

        admin = db.query(User).filter(User.email == "admin@vignan.ac.in").first()
        if not admin:
            db.add(
                User(
                    name="admin",
                    username="admin",
                    email="admin@vignan.ac.in",
                    password=get_password_hash("admin"),
                    role="admin",
                    security_grid=json.dumps(generate_security_grid("admin@vignan.ac.in")),
                )
            )
        else:
            admin.name = "admin"
            admin.username = "admin"
            admin.password = get_password_hash("admin")
            admin.role = "admin"
            if is_legacy_shared_grid(admin.security_grid):
                admin.security_grid = json.dumps(generate_security_grid(admin.email))

        password_hash = get_password_hash(FACULTY_PASSWORD)
        created = 0
        updated = 0
        deleted = 0
        normalized_students = 0

        students = db.query(Student).all()
        for student in students:
            normalized_name = (student.counselor_name or "").strip()
            canonical_name = canonical_names.get(normalized_name.casefold())
            if canonical_name and student.counselor_name != canonical_name:
                student.counselor_name = canonical_name
                normalized_students += 1

        username_updates: list[tuple[User, str]] = []
        for faculty_name in counselor_names:
            email = faculty_email(faculty_name)
            username = faculty_login_ids[faculty_name]
            user = db.query(User).filter(User.email == email).first()
            if not user:
                db.add(
                    User(
                        name=faculty_name,
                        username=username,
                        email=email,
                        password=password_hash,
                        role="faculty",
                        security_grid=json.dumps(generate_security_grid(email)),
                    )
                )
                created += 1
                continue

            if user.name != faculty_name or user.role != "faculty":
                user.name = faculty_name
                user.role = "faculty"
                updated += 1
            if user.username != username:
                username_updates.append((user, username))
            if is_legacy_shared_grid(user.security_grid):
                user.security_grid = json.dumps(generate_security_grid(email))

        for user, _ in username_updates:
            user.username = f"__tmp__{user.id}_{secrets.token_hex(4)}"
        if username_updates:
            db.flush()
            for user, username in username_updates:
                user.username = username

        stale_faculty_users = (
            db.query(User)
            .filter(User.role == "faculty")
            .all()
        )
        for faculty in stale_faculty_users:
            if faculty.email not in active_emails:
                db.delete(faculty)
                deleted += 1

        db.commit()
        print(
            f"Synced {len(counselor_names)} active counselor logins "
            f"(created={created}, updated={updated}, deleted={deleted}, "
            f"normalized_students={normalized_students})."
        )
    finally:
        db.close()


if __name__ == "__main__":
    sync_faculty_assignments()
