from app.db.session import SessionLocal
from app.models.subject_attendance import SubjectAttendance
from app.utils.init_db import init_db


def _assignment_scores_from_average(t5_average: float) -> tuple[int, int, int, int]:
    target_total = int(round(t5_average * 4))
    base_score = target_total // 4
    remainder = target_total % 4
    scores = [base_score] * 4
    for index in range(remainder):
        scores[index] += 1
    return tuple(scores)


def backfill_t5_assignment_scores() -> dict[str, int]:
    init_db()
    db = SessionLocal()
    try:
        updated_rows = 0
        subject_rows = db.query(SubjectAttendance).all()

        for subject_row in subject_rows:
            assignments_need_backfill = (
                subject_row.t5_assignment_1 == 0
                and subject_row.t5_assignment_2 == 0
                and subject_row.t5_assignment_3 == 0
                and subject_row.t5_assignment_4 == 0
            ) or (
                subject_row.t5_assignment_1 == subject_row.t5_marks
                and subject_row.t5_assignment_2 == subject_row.t5_marks
                and subject_row.t5_assignment_3 == subject_row.t5_marks
                and subject_row.t5_assignment_4 == subject_row.t5_marks
            )
            if not assignments_need_backfill or subject_row.t5_marks <= 0:
                continue

            # Historical rows only stored the T5 average. Reconstruct four
            # whole-number assignment scores whose average matches that value.
            (
                subject_row.t5_assignment_1,
                subject_row.t5_assignment_2,
                subject_row.t5_assignment_3,
                subject_row.t5_assignment_4,
            ) = _assignment_scores_from_average(subject_row.t5_marks)
            updated_rows += 1

        db.commit()
        return {"updated_subject_rows": updated_rows}
    finally:
        db.close()


if __name__ == "__main__":
    summary = backfill_t5_assignment_scores()
    print(f"Backfilled T5 assignment scores for {summary['updated_subject_rows']} subject rows.")
