from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.student import Student
from app.models.user import User
from app.schemas.recommendation import AdvisingMeetingPlan, RecommendationResponse


def _heuristic_overview_risk(student: Student) -> tuple[str, float]:
    academic_financial_points = 0
    lms_points = 0

    if student.attendance < 65:
        academic_financial_points += 3
    elif student.attendance < 75:
        academic_financial_points += 2
    elif student.attendance < 85:
        academic_financial_points += 1

    if student.gpa < 5.5:
        academic_financial_points += 2
    elif student.gpa < 7.0:
        academic_financial_points += 1

    if student.lms_activity:
        if (
            student.lms_activity.weekly_logins < 7
            or student.lms_activity.assignment_submission_rate < 65
            or student.lms_activity.missed_assignments >= 4
        ):
            lms_points += 1

    if student.financial and (student.financial.fee_due > 0 or student.financial.payment_delay_days > 0):
        academic_financial_points += 1

    total_points = academic_financial_points + lms_points

    if (
        student.attendance >= 80
        and student.gpa >= 8.0
        and student.lms_activity
        and student.lms_activity.assignment_submission_rate >= 80
        and student.financial
        and student.financial.fee_due <= 0
        and student.financial.payment_delay_days <= 0
    ):
        return "Safe", 0.15
    if academic_financial_points >= 4:
        return "High", 0.85
    if total_points >= 2:
        return "Medium", 0.65
    if total_points == 1:
        return "Low", 0.35
    return "Low", 0.35


def _academic_recommendations(student: Student) -> list[str]:
    recommendations: list[str] = []
    if student.attendance < 65:
        recommendations.append("Urgently improve attendance above 75% with faculty follow-up and weekly monitoring.")
    elif student.attendance < 75:
        recommendations.append("Improve attendance to at least 85% through structured class participation goals.")
    elif student.attendance < 85:
        recommendations.append("Attendance is slightly below the safe threshold; aim to consistently stay above 85%.")
    if student.gpa < 6.5 or student.marks < 60:
        recommendations.append("Schedule faculty mentoring for weak subjects and revise fundamentals twice a week.")
    if student.lms_activity and student.lms_activity.assignment_submission_rate < 80:
        recommendations.append("Complete pending LMS assignments and maintain a submission rate above 90%.")
    if not recommendations:
        recommendations.append("Maintain the current academic performance with monthly progress reviews.")
    return recommendations


def _career_recommendations(student: Student) -> list[str]:
    interest = student.career_interest.lower()
    base = {
        "data": "Explore data analyst, BI analyst, and junior ML roles; strengthen SQL, Python, and visualization.",
        "software": "Focus on software engineering pathways with stronger problem-solving and full-stack project work.",
        "business": "Develop communication, analytics, and spreadsheet modeling for business analyst roles.",
        "design": "Build a portfolio around UI/UX, design systems, and user research case studies.",
    }
    matched = next((value for key, value in base.items() if key in interest), None)
    recommendations = [matched] if matched else ["Identify one target career path and map the required technical skills for that role."]
    if "python" not in student.skills.lower():
        recommendations.append("Add Python fundamentals to improve career flexibility and analytical capability.")
    return recommendations


def _learning_pathways(student: Student) -> list[str]:
    pathways: list[str] = []
    if student.marks < 65:
        pathways.append("Assign remedial subject modules and short quizzes for core academic concepts.")
    if student.lms_activity and student.lms_activity.avg_time_spent < 4:
        pathways.append("Follow a guided 30-minute daily LMS study plan with progress checkpoints.")
    if student.attendance < 85:
        pathways.append("Recommend attendance-linked microlearning materials for missed classroom topics.")
    if not pathways:
        pathways.append("Recommend advanced elective courses and project-based learning aligned with strengths.")
    return pathways


def _meeting_plan(student: Student, resolved_risk_level: str) -> AdvisingMeetingPlan:
    issues: list[tuple[int, str]] = []
    faculty_questions: list[str] = []
    student_actions: list[str] = []

    def add_issue(priority: int, text: str) -> None:
        issues.append((priority, text))

    if student.attendance < 65:
        add_issue(100, "the attendance drop and missed classroom engagement")
        faculty_questions.append("What is causing repeated absence from classes right now?")
        faculty_questions.append("Which days or subjects are being missed most often?")
        student_actions.append("Attend every class for the next two weeks and share attendance progress with faculty.")
    elif student.attendance < 75:
        add_issue(70, "attendance consistency before it becomes a severe issue")
        faculty_questions.append("What is preventing regular attendance each week?")
        student_actions.append("Follow a weekly attendance target and review it with faculty.")
    elif student.attendance < 85:
        add_issue(35, "improving attendance above the safe 85% threshold")
        faculty_questions.append("What support would help you stay consistently above 85% attendance?")
        student_actions.append("Maintain attendance above 85% for the next review cycle.")

    if student.gpa < 6.5 or student.marks < 60:
        add_issue(90, "weak academic performance in core subjects")
        faculty_questions.append("Which subjects feel most difficult at the moment?")
        faculty_questions.append("How many focused study hours are you able to maintain each week?")
        student_actions.append("Prepare a subject-wise study timetable and meet faculty for weak subjects twice a week.")

    if student.lms_activity and student.lms_activity.assignment_submission_rate < 80:
        add_issue(80, "pending LMS work and low assignment completion")
        faculty_questions.append("Why are LMS assignments getting delayed or missed?")
        student_actions.append("Complete pending LMS assignments before the next faculty check-in.")

    if student.lms_activity and student.lms_activity.avg_time_spent < 4:
        add_issue(60, "low LMS study time")
        faculty_questions.append("How much time are you able to spend daily on LMS learning?")
        student_actions.append("Follow a 30-minute daily LMS study routine.")

    fee_pending = bool(student.financial and student.financial.fee_due > 0)
    if fee_pending:
        add_issue(85, "the pending fee issue affecting continuity")
        faculty_questions.append("Is there any financial difficulty delaying fee payment?")
        student_actions.append("Clear the pending fee issue or meet DEO/accounts for support immediately.")

    if not issues:
        add_issue(10, "maintaining the current positive academic progress")
        faculty_questions.append("Which current habits are helping you perform well consistently?")
        student_actions.append("Continue the present academic routine and review progress monthly.")

    issues.sort(key=lambda item: item[0], reverse=True)
    discuss_first = f"Start with {issues[0][1]}."
    parent_involvement_needed = resolved_risk_level == "High"
    if parent_involvement_needed:
        parent_involvement_reason = "Parent involvement is recommended because the student is currently in the high-risk category."
    else:
        parent_involvement_reason = "Parent involvement is not necessary at this stage because the student is not in the high-risk category."

    unique_questions = list(dict.fromkeys(faculty_questions))[:4]
    unique_actions = list(dict.fromkeys(student_actions))[:4]

    return AdvisingMeetingPlan(
        discuss_first=discuss_first,
        faculty_questions=unique_questions,
        student_actions=unique_actions,
        parent_involvement_needed=parent_involvement_needed,
        parent_involvement_reason=parent_involvement_reason,
    )


def build_recommendations(student: Student) -> RecommendationResponse:
    latest_prediction = max(student.predictions, key=lambda item: item.created_at) if student.predictions else None
    fallback_risk_level, _ = _heuristic_overview_risk(student)
    resolved_risk_level = latest_prediction.risk_level if latest_prediction else fallback_risk_level
    return RecommendationResponse(
        academic=_academic_recommendations(student),
        career=_career_recommendations(student),
        learning_pathways=_learning_pathways(student),
        meeting_plan=_meeting_plan(student, resolved_risk_level),
    )


def get_student_recommendations(db: Session, student_id: int, current_user: User) -> RecommendationResponse:
    query = db.query(Student).options(
        joinedload(Student.predictions),
        joinedload(Student.lms_activity),
        joinedload(Student.financial),
    ).filter(Student.id == student_id)
    if current_user.role == "faculty":
        query = query.filter(Student.counselor_name == current_user.name)
    student = query.first()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found or not assigned")
    return build_recommendations(student)
