import random

from app.db.session import SessionLocal
from app.models.lms_activity import LMSActivity
from app.models.student import Student
from app.utils.init_db import init_db

TOTAL_CODING_TESTS = 6
QUESTIONS_PER_TEST = 10
TOTAL_QUESTIONS = TOTAL_CODING_TESTS * QUESTIONS_PER_TEST
MIN_CORRECT_SOLUTIONS = 18


def _random_correct_solution_count() -> int:
    return random.randint(MIN_CORRECT_SOLUTIONS, TOTAL_QUESTIONS)


def _submission_rate_from_solved_count(solved_count: int) -> float:
    capped = max(0, min(solved_count, TOTAL_QUESTIONS))
    return round((capped / TOTAL_QUESTIONS) * 100, 2)


def _bounded(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _lms_profile_from_student(student: Student) -> tuple[int, float, float, int]:
    attendance = float(student.attendance or 0)
    gpa = float(student.gpa or 0)
    submission_rate = _submission_rate_from_solved_count(_random_correct_solution_count())

    # Keep LMS correlated with attendance/GPA so risk bands feel consistent.
    weekly_logins = int(round(_bounded(4 + attendance / 10 + random.uniform(-2, 2), 4, 14)))
    avg_time_spent = round(_bounded(1.5 + attendance / 18 + gpa / 5 + random.uniform(-0.75, 0.75), 2.0, 9.5), 2)
    submission_rate = round(_bounded((submission_rate * 0.45) + (attendance * 0.4) + (gpa * 3), 55, 98), 2)
    missed_assignments = int(round(_bounded((100 - submission_rate) / 12 + random.uniform(-1, 1), 0, 4)))

    if attendance >= 85 and gpa >= 8.0:
        weekly_logins = max(weekly_logins, 10)
        avg_time_spent = max(avg_time_spent, 6.0)
        submission_rate = max(submission_rate, 82.0)
        missed_assignments = min(missed_assignments, 1)

    return weekly_logins, avg_time_spent, submission_rate, missed_assignments


def randomize_lms_activity_percentage() -> dict[str, int]:
    init_db()
    db = SessionLocal()
    try:
        updated_students = 0
        created_lms_rows = 0

        students = db.query(Student).all()
        for student in students:
            if student.lms_activity is None:
                student.lms_activity = LMSActivity(
                    weekly_logins=0,
                    avg_time_spent=0.0,
                    assignment_submission_rate=0.0,
                    missed_assignments=0,
                )
                created_lms_rows += 1

            weekly_logins, avg_time_spent, submission_rate, missed_assignments = _lms_profile_from_student(student)
            student.lms_activity.weekly_logins = weekly_logins
            student.lms_activity.avg_time_spent = avg_time_spent
            student.lms_activity.assignment_submission_rate = submission_rate
            student.lms_activity.missed_assignments = missed_assignments
            updated_students += 1

        db.commit()
        return {
            "updated_students": updated_students,
            "created_lms_rows": created_lms_rows,
        }
    finally:
        db.close()


if __name__ == "__main__":
    summary = randomize_lms_activity_percentage()
    print(
        f"Randomized LMS percentage for {summary['updated_students']} students "
        f"and created {summary['created_lms_rows']} LMS rows."
    )
