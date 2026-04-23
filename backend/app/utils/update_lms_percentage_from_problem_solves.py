from app.db.session import SessionLocal
from app.models.lms_activity import LMSActivity
from app.models.student import Student
from app.utils.init_db import init_db

TOTAL_CODING_TESTS = 6
QUESTIONS_PER_TEST = 10
TOTAL_QUESTIONS = TOTAL_CODING_TESTS * QUESTIONS_PER_TEST


def _submission_rate_from_solved_count(solved_count: int) -> float:
    capped = max(0, min(solved_count, TOTAL_QUESTIONS))
    return round((capped / TOTAL_QUESTIONS) * 100, 2)


def update_lms_percentage_from_problem_solves() -> dict[str, int]:
    init_db()
    db = SessionLocal()
    try:
        updated_students = 0
        created_lms_rows = 0

        students = db.query(Student).all()
        for student in students:
            solved_count = int(max(student.codechef_problems_solved or 0, 0))

            if student.lms_activity is None:
                student.lms_activity = LMSActivity(
                    weekly_logins=0,
                    avg_time_spent=0.0,
                    assignment_submission_rate=0.0,
                    missed_assignments=0,
                )
                created_lms_rows += 1

            student.lms_activity.assignment_submission_rate = _submission_rate_from_solved_count(solved_count)
            updated_students += 1

        db.commit()
        return {
            "updated_students": updated_students,
            "created_lms_rows": created_lms_rows,
        }
    finally:
        db.close()


if __name__ == "__main__":
    summary = update_lms_percentage_from_problem_solves()
    print(
        f"Updated LMS percentage for {summary['updated_students']} students "
        f"and created {summary['created_lms_rows']} LMS rows."
    )
