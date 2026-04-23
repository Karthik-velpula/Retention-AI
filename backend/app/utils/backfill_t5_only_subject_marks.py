import random

from app.db.session import SessionLocal
from app.models.subject_attendance import SubjectAttendance
from app.utils.init_db import init_db

TARGET_SUBJECTS = {
    "22CS958 CLSA",
    "22TP302 QALR",
}
T5_ASSIGNMENT_COUNT = 4
T5_ASSIGNMENT_MAX = 20


def _random_score(max_marks: int) -> float:
    lower_bound = max(0, round(max_marks * 0.55))
    return float(random.randint(lower_bound, max_marks))


def _random_t5_assignment_scores() -> list[float]:
    return [_random_score(T5_ASSIGNMENT_MAX) for _ in range(T5_ASSIGNMENT_COUNT)]


def backfill_t5_only_subject_marks() -> dict[str, int]:
    init_db()
    db = SessionLocal()
    try:
        updated_rows = 0
        subject_rows = (
            db.query(SubjectAttendance)
            .filter(SubjectAttendance.subject_name.in_(TARGET_SUBJECTS))
            .all()
        )

        for subject_row in subject_rows:
            t5_assignment_scores = _random_t5_assignment_scores()
            (
                subject_row.t5_assignment_1,
                subject_row.t5_assignment_2,
                subject_row.t5_assignment_3,
                subject_row.t5_assignment_4,
            ) = t5_assignment_scores
            subject_row.pre_t1_marks = 0
            subject_row.t1_marks = 0
            subject_row.t2_marks = 0
            subject_row.t3_marks = 0
            subject_row.t4_marks = 0
            subject_row.t5_marks = round(sum(t5_assignment_scores) / T5_ASSIGNMENT_COUNT, 2)
            subject_row.total_marks = subject_row.t5_marks
            updated_rows += 1

        db.commit()
        return {"updated_subject_rows": updated_rows}
    finally:
        db.close()


if __name__ == "__main__":
    summary = backfill_t5_only_subject_marks()
    print(f"Updated T5-only marks for {summary['updated_subject_rows']} subject rows.")
