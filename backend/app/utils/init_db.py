import json
import secrets

from sqlalchemy import inspect, text

from app.core.faculty_assignments import (
    FACULTY_NAMES,
    FACULTY_PASSWORD,
    active_counselor_names,
    build_faculty_login_ids,
    faculty_email,
)
from app.core.security import generate_security_grid, get_password_hash, is_legacy_shared_grid
from app.db.base import Student, User
from app.db.session import Base, SessionLocal, engine


def repair_swapped_student_metrics() -> int:
    inspector = inspect(engine)
    if "students" not in inspector.get_table_names():
        return 0

    student_columns = {column["name"] for column in inspector.get_columns("students")}
    if not {"id", "gpa", "attendance"}.issubset(student_columns):
        return 0

    mysql_repair_sql = """
        UPDATE students AS s
        JOIN (
            SELECT id, gpa AS old_gpa, attendance AS old_attendance
            FROM students
            WHERE gpa > 10 AND attendance <= 10
        ) AS swapped ON swapped.id = s.id
        SET s.gpa = swapped.old_attendance,
            s.attendance = swapped.old_gpa
    """
    generic_repair_sql = """
        UPDATE students
        SET gpa = attendance,
            attendance = gpa
        WHERE gpa > 10 AND attendance <= 10
    """

    with engine.begin() as connection:
        repair_sql = mysql_repair_sql if connection.dialect.name in {"mysql", "mariadb"} else generic_repair_sql
        result = connection.execute(text(repair_sql))
        return int(result.rowcount or 0)


def init_db() -> None:
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
        if "student_mobile" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN student_mobile VARCHAR(30) NOT NULL DEFAULT ''"))
        if "parent_mobile" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN parent_mobile VARCHAR(30) NOT NULL DEFAULT ''"))
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
        if "pre_t1_marks" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN pre_t1_marks FLOAT NOT NULL DEFAULT 0"))
        if "t1_marks" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN t1_marks FLOAT NOT NULL DEFAULT 0"))
        if "t2_marks" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN t2_marks FLOAT NOT NULL DEFAULT 0"))
        if "t3_marks" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN t3_marks FLOAT NOT NULL DEFAULT 0"))
        if "t4_marks" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN t4_marks FLOAT NOT NULL DEFAULT 0"))
        if "t5_marks" not in student_columns:
            connection.execute(text("ALTER TABLE students ADD COLUMN t5_marks FLOAT NOT NULL DEFAULT 0"))
    student_indexes = {index["name"]: index for index in inspector.get_indexes("students")}
    with engine.begin() as connection:
        email_index = student_indexes.get("ix_students_email")
        if email_index and email_index.get("unique"):
            connection.execute(text("DROP INDEX ix_students_email ON students"))
            connection.execute(text("CREATE INDEX ix_students_email ON students (email)"))
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    with engine.begin() as connection:
        if "username" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(40) NULL"))
        if "security_grid" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN security_grid VARCHAR(1000) NOT NULL DEFAULT '{}'"))
        if "last_login_at" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN last_login_at DATETIME NULL"))
        if "token_version" not in user_columns:
            connection.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"))
    user_indexes = {index["name"]: index for index in inspector.get_indexes("users")}
    with engine.begin() as connection:
        if "ix_users_username" not in user_indexes:
            connection.execute(text("CREATE UNIQUE INDEX ix_users_username ON users (username)"))
    otp_columns = {column["name"] for column in inspector.get_columns("password_reset_otps")}
    with engine.begin() as connection:
        if "purpose" not in otp_columns:
            connection.execute(text("ALTER TABLE password_reset_otps ADD COLUMN purpose VARCHAR(40) NOT NULL DEFAULT 'password_reset'"))
    if "interventions" in inspector.get_table_names():
        intervention_columns = {column["name"] for column in inspector.get_columns("interventions")}
        if "follow_up_outcome" not in intervention_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE interventions ADD COLUMN follow_up_outcome VARCHAR(20) NULL"))
    if "subject_attendance" in inspector.get_table_names():
        subject_attendance_columns = {column["name"] for column in inspector.get_columns("subject_attendance")}
        with engine.begin() as connection:
            if "pre_t1_marks" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN pre_t1_marks FLOAT NOT NULL DEFAULT 0"))
            if "t1_marks" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN t1_marks FLOAT NOT NULL DEFAULT 0"))
            if "t2_marks" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN t2_marks FLOAT NOT NULL DEFAULT 0"))
            if "t3_marks" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN t3_marks FLOAT NOT NULL DEFAULT 0"))
            if "t4_marks" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN t4_marks FLOAT NOT NULL DEFAULT 0"))
            if "t5_marks" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN t5_marks FLOAT NOT NULL DEFAULT 0"))
            if "t5_assignment_1" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN t5_assignment_1 FLOAT NOT NULL DEFAULT 0"))
            if "t5_assignment_2" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN t5_assignment_2 FLOAT NOT NULL DEFAULT 0"))
            if "t5_assignment_3" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN t5_assignment_3 FLOAT NOT NULL DEFAULT 0"))
            if "t5_assignment_4" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN t5_assignment_4 FLOAT NOT NULL DEFAULT 0"))
            if "total_marks" not in subject_attendance_columns:
                connection.execute(text("ALTER TABLE subject_attendance ADD COLUMN total_marks FLOAT NOT NULL DEFAULT 0"))
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email.in_(["admin@retentionai.com", "admin@vignan.ac.in"])).first()
        if not admin:
            admin_grid = json.dumps(generate_security_grid("admin@vignan.ac.in"))
            db.add(
                User(
                    name="admin",
                    username="admin",
                    email="admin@vignan.ac.in",
                    password=get_password_hash("admin"),
                    role="admin",
                    security_grid=admin_grid,
                )
            )
        else:
            admin.name = "admin"
            admin.username = "admin"
            admin.email = "admin@vignan.ac.in"
            admin.password = get_password_hash("admin")
            admin.role = "admin"
            if is_legacy_shared_grid(admin.security_grid):
                admin.security_grid = json.dumps(generate_security_grid(admin.email))
        counselor_names = active_counselor_names(FACULTY_NAMES)
        student_assignments = db.query(
            Student.year,
            Student.section,
            Student.counselor_name,
            Student.registration_number,
        ).all()
        faculty_login_ids = build_faculty_login_ids(student_assignments, counselor_names)
        faculty_password_hash = get_password_hash(FACULTY_PASSWORD)
        active_faculty_emails = {faculty_email(name) for name in counselor_names}
        username_updates: list[tuple[User, str]] = []
        for faculty_name in counselor_names:
            email = faculty_email(faculty_name)
            username = faculty_login_ids[faculty_name]
            faculty = db.query(User).filter(User.email == email).first()
            if not faculty:
                db.add(
                    User(
                        name=faculty_name,
                        username=username,
                        email=email,
                        password=faculty_password_hash,
                        role="faculty",
                        security_grid=json.dumps(generate_security_grid(email)),
                    )
                )
            else:
                faculty.name = faculty_name
                faculty.email = email
                faculty.role = "faculty"
                if faculty.username != username:
                    username_updates.append((faculty, username))
                if is_legacy_shared_grid(faculty.security_grid):
                    faculty.security_grid = json.dumps(generate_security_grid(email))
        for faculty, _ in username_updates:
            faculty.username = f"__tmp__{faculty.id}_{secrets.token_hex(4)}"
        if username_updates:
            db.flush()
            for faculty, username in username_updates:
                faculty.username = username
        legacy_generic_faculty = db.query(User).filter(User.email == "faculty@retentionai.com").first()
        if legacy_generic_faculty:
            db.delete(legacy_generic_faculty)
        stale_faculty_users = (
            db.query(User)
            .filter(User.role == "faculty")
            .all()
        )
        for faculty in stale_faculty_users:
            if faculty.email not in active_faculty_emails:
                db.delete(faculty)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
