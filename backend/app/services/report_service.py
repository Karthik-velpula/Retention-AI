import json
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.core.faculty_assignments import (
    FACULTY_PASSWORD,
    TEST_FACULTY_EMAIL,
    TEST_FACULTY_NAME,
    TEST_FACULTY_PASSWORD,
)
from app.models.user import User
from app.models.student import Student
from app.models.prediction import Prediction
from app.schemas.analytics import AnalyticsResponse
from app.schemas.intervention import InterventionStudentOverview


def generate_pdf_report(analytics: AnalyticsResponse) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    _, height = A4

    pdf.setTitle("Student Retention Analytics Report")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(0.8 * inch, height - 1.0 * inch, "Student Retention Analytics Report")

    pdf.setFont("Helvetica", 11)
    lines = [
        f"Total students: {analytics.kpis.total_students}",
        f"High risk students: {analytics.kpis.high_risk_students}",
        f"Medium risk students: {analytics.kpis.medium_risk_students}",
        f"Low risk students: {analytics.kpis.low_risk_students}",
        f"Average GPA: {analytics.kpis.average_gpa}",
        f"Average attendance: {analytics.kpis.average_attendance}%",
        "",
        "Department risk scores:",
    ]

    y = height - 1.5 * inch
    for line in lines:
        pdf.drawString(0.8 * inch, y, line)
        y -= 0.28 * inch

    for item in analytics.department_risk:
        pdf.drawString(1.0 * inch, y, f"- {item.label}: {item.value}")
        y -= 0.24 * inch

    pdf.showPage()
    pdf.save()
    buffer.seek(0)
    return buffer


def generate_security_grid_report(users: list[User]) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setTitle("User Security Grid Report")
    for index, user in enumerate(users):
        grid = json.loads(user.security_grid or "{}")
        if index > 0:
            pdf.showPage()

        outer_x = 0.65 * inch
        outer_y = 0.7 * inch
        outer_width = width - 1.3 * inch
        outer_height = height - 1.35 * inch
        pdf.setFillColorRGB(0.975, 0.98, 1)
        pdf.roundRect(outer_x, outer_y, outer_width, outer_height, 24, stroke=0, fill=1)

        header_height = 0.9 * inch
        pdf.setFillColorRGB(0.19, 0.28, 0.62)
        pdf.roundRect(outer_x + 0.18 * inch, height - 1.45 * inch, outer_width - 0.36 * inch, header_height, 16, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont("Helvetica-Bold", 19)
        pdf.drawString(outer_x + 0.42 * inch, height - 0.98 * inch, "Security Grid Report")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(outer_x + 0.42 * inch, height - 1.22 * inch, "Confidential personal grid for secure retention portal access")

        info_y = height - 2.35 * inch
        info_height = 0.95 * inch
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setStrokeColorRGB(0.75, 0.79, 0.88)
        pdf.roundRect(outer_x + 0.18 * inch, info_y, outer_width - 0.36 * inch, info_height, 16, stroke=1, fill=1)
        pdf.setFillColorRGB(0.12, 0.16, 0.25)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(outer_x + 0.38 * inch, info_y + 0.58 * inch, f"User: {user.name}")
        pdf.setFont("Helvetica", 10.5)
        pdf.drawString(outer_x + 0.38 * inch, info_y + 0.3 * inch, f"Email: {user.email}")
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawRightString(outer_x + outer_width - 0.38 * inch, info_y + 0.58 * inch, f"Role: {user.role.title()}")

        note_y = info_y - 0.5 * inch
        pdf.setFillColorRGB(0.33, 0.39, 0.56)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(outer_x + 0.22 * inch, note_y, "Use these values during login when the system asks for any two grid positions.")

        y = info_y - 1.05 * inch
        card_width = (outer_width - 0.7 * inch) / 3
        card_height = 0.78 * inch
        positions = sorted(grid.keys(), key=lambda value: int(value[1:]))
        for grid_index, position in enumerate(positions):
            column = grid_index % 3
            row = grid_index // 3
            x = outer_x + 0.22 * inch + column * card_width
            current_y = y - row * (card_height + 0.14 * inch)
            pdf.setFillColorRGB(1, 1, 1)
            pdf.setStrokeColorRGB(0.64, 0.68, 0.77)
            pdf.roundRect(x, current_y, card_width - 0.12 * inch, card_height, 10, stroke=1, fill=1)
            pdf.setFillColorRGB(0.19, 0.28, 0.62)
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(x + 0.14 * inch, current_y + 0.49 * inch, position)
            pdf.setFillColorRGB(0.07, 0.13, 0.22)
            pdf.setFont("Helvetica-Bold", 15)
            pdf.drawString(x + 0.14 * inch, current_y + 0.2 * inch, grid[position])

        pdf.setFont("Helvetica", 9)
        pdf.setFillColorRGB(0.4, 0.45, 0.56)
        pdf.drawString(outer_x + 0.22 * inch, outer_y + 0.12 * inch, "Keep this grid private. Use it only for your secure retention portal login.")

    pdf.save()
    buffer.seek(0)
    return buffer


def generate_user_credentials_report(users: list[User]) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    visible_users = [user for user in users if user.email != TEST_FACULTY_EMAIL and user.name != TEST_FACULTY_NAME]
    pdf.setTitle("User Credentials Report")

    for index, user in enumerate(visible_users):
        grid = json.loads(user.security_grid or "{}")
        if index > 0:
            pdf.showPage()

        outer_x = 0.65 * inch
        outer_y = 0.7 * inch
        outer_width = width - 1.3 * inch
        outer_height = height - 1.35 * inch

        pdf.setFillColorRGB(0.98, 0.99, 1)
        pdf.roundRect(outer_x, outer_y, outer_width, outer_height, 24, stroke=0, fill=1)

        header_height = 0.95 * inch
        pdf.setFillColorRGB(0.14, 0.25, 0.56)
        pdf.roundRect(outer_x + 0.18 * inch, height - 1.5 * inch, outer_width - 0.36 * inch, header_height, 16, stroke=0, fill=1)
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(outer_x + 0.42 * inch, height - 0.98 * inch, "Portal Credentials Report")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(outer_x + 0.42 * inch, height - 1.22 * inch, "Login ID, seeded password, and security grid for retention portal access")

        info_y = height - 2.4 * inch
        info_width = outer_width - 0.36 * inch
        info_height = 1.55 * inch
        pdf.setFillColorRGB(1, 1, 1)
        pdf.setStrokeColorRGB(0.75, 0.79, 0.88)
        pdf.roundRect(outer_x + 0.18 * inch, info_y, info_width, info_height, 16, stroke=1, fill=1)

        password_hint = "Not available"
        if user.role == "admin":
            password_hint = "admin"
        elif user.role == "faculty":
            password_hint = TEST_FACULTY_PASSWORD if user.email == TEST_FACULTY_EMAIL else FACULTY_PASSWORD

        pdf.setFillColorRGB(0.12, 0.16, 0.25)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(outer_x + 0.38 * inch, info_y + 1.08 * inch, f"User: {user.name}")
        pdf.setFont("Helvetica", 10.5)
        pdf.drawString(outer_x + 0.38 * inch, info_y + 0.8 * inch, f"Login ID: {user.username or user.email}")
        pdf.drawString(outer_x + 0.38 * inch, info_y + 0.52 * inch, f"Role: {user.role.title()}")
        pdf.drawString(outer_x + 0.38 * inch, info_y + 0.24 * inch, f"Seeded Password: {password_hint}")

        pdf.setFillColorRGB(0.33, 0.39, 0.56)
        pdf.setFont("Helvetica", 9.5)
        pdf.drawString(
            outer_x + 0.2 * inch,
            info_y - 0.28 * inch,
            "Note: the current actual password cannot be recovered from the database if the user has changed it later.",
        )
        pdf.drawString(
            outer_x + 0.2 * inch,
            info_y - 0.48 * inch,
            "Use the security grid below when the login screen asks for any two positions.",
        )

        y = info_y - 1.0 * inch
        card_width = (outer_width - 0.7 * inch) / 3
        card_height = 0.78 * inch
        positions = sorted(grid.keys(), key=lambda value: int(value[1:]) if value[1:].isdigit() else value)
        for grid_index, position in enumerate(positions):
            column = grid_index % 3
            row = grid_index // 3
            x = outer_x + 0.22 * inch + column * card_width
            current_y = y - row * (card_height + 0.14 * inch)
            pdf.setFillColorRGB(1, 1, 1)
            pdf.setStrokeColorRGB(0.64, 0.68, 0.77)
            pdf.roundRect(x, current_y, card_width - 0.12 * inch, card_height, 10, stroke=1, fill=1)
            pdf.setFillColorRGB(0.14, 0.25, 0.56)
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(x + 0.14 * inch, current_y + 0.49 * inch, position)
            pdf.setFillColorRGB(0.07, 0.13, 0.22)
            pdf.setFont("Helvetica-Bold", 15)
            pdf.drawString(x + 0.14 * inch, current_y + 0.2 * inch, grid[position])

        pdf.setFont("Helvetica", 9)
        pdf.setFillColorRGB(0.4, 0.45, 0.56)
        pdf.drawString(outer_x + 0.22 * inch, outer_y + 0.12 * inch, "Keep this report private. It contains sensitive login information.")

    pdf.save()
    buffer.seek(0)
    return buffer


def _wrap_text(text: str, limit: int = 95) -> list[str]:
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= limit:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def generate_intervention_history_report(
    records: list[InterventionStudentOverview],
    counselor_name: str,
    student_name: str | None = None,
) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    def ensure_space(current_y: float, required_height: float) -> float:
        if current_y - required_height > 0.75 * inch:
            return current_y
        pdf.showPage()
        return height - 0.9 * inch

    title = "Intervention History Report"
    subtitle = f"Counselor: {counselor_name}"
    if student_name:
        subtitle = f"{subtitle} | Student: {student_name}"

    pdf.setTitle(title)
    y = height - 0.9 * inch
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(0.75 * inch, y, title)
    y -= 0.3 * inch
    pdf.setFont("Helvetica", 11)
    pdf.drawString(0.75 * inch, y, subtitle)
    y -= 0.3 * inch
    pdf.drawString(0.75 * inch, y, f"Students in report: {len(records)}")
    y -= 0.45 * inch

    if not records:
        pdf.setFont("Helvetica", 11)
        pdf.drawString(0.75 * inch, y, "No intervention history is available for the selected scope.")
        pdf.save()
        buffer.seek(0)
        return buffer

    for student_index, record in enumerate(records):
        history_entries = record.history or []
        latest_note = record.intervention.notes.strip() if record.intervention and record.intervention.notes else ""
        block_height = 1.25 * inch + max(len(history_entries), 1) * 0.95 * inch
        if latest_note:
            block_height += 0.45 * inch

        y = ensure_space(y, block_height)

        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(0.75 * inch, y, record.student_name)
        pdf.setFont("Helvetica", 10.5)
        pdf.drawRightString(width - 0.75 * inch, y, f"Risk: {record.latest_risk_level}")
        y -= 0.22 * inch
        pdf.drawString(0.75 * inch, y, f"Registration Number: {record.registration_number}")
        y -= 0.2 * inch
        pdf.drawString(0.75 * inch, y, f"Attendance: {record.attendance:.0f}%")
        y -= 0.2 * inch
        pdf.drawString(0.75 * inch, y, f"Updated By: {record.intervention.updated_by if record.intervention else '-'}")
        y -= 0.25 * inch

        if latest_note:
            pdf.setFont("Helvetica-Bold", 10.5)
            pdf.drawString(0.9 * inch, y, "Latest Note")
            y -= 0.18 * inch
            pdf.setFont("Helvetica", 10)
            for line in _wrap_text(latest_note):
                y = ensure_space(y, 0.2 * inch)
                pdf.drawString(1.05 * inch, y, line)
                y -= 0.17 * inch
            y -= 0.08 * inch

        if history_entries:
            for entry in history_entries:
                y = ensure_space(y, 0.7 * inch)
                pdf.setFont("Helvetica-Bold", 10.5)
                pdf.drawString(0.9 * inch, y, f"{entry.changed_by} | {entry.created_at.strftime('%d %b %Y, %I:%M %p')}")
                y -= 0.18 * inch
                pdf.setFont("Helvetica", 10)
                pdf.drawString(1.05 * inch, y, f"Changed: {entry.changed_fields}")
                y -= 0.17 * inch
                for line in _wrap_text(entry.change_summary):
                    y = ensure_space(y, 0.2 * inch)
                    pdf.drawString(1.05 * inch, y, line)
                    y -= 0.17 * inch
                y -= 0.08 * inch
        else:
            pdf.setFont("Helvetica", 10)
            pdf.drawString(0.9 * inch, y, "No intervention history available for this student.")
            y -= 0.22 * inch

        if student_index < len(records) - 1:
            y -= 0.12 * inch
            pdf.line(0.75 * inch, y, width - 0.75 * inch, y)
            y -= 0.28 * inch

    pdf.save()
    buffer.seek(0)
    return buffer


def generate_parent_student_report(student: Student, prediction: Prediction) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left = 0.7 * inch
    right = width - 0.7 * inch
    top = height - 0.8 * inch
    bottom = 0.7 * inch

    def new_page() -> float:
        pdf.showPage()
        pdf.setFont("Helvetica", 10)
        return top

    def ensure_space(current_y: float, required_height: float) -> float:
        if current_y - required_height >= bottom:
            return current_y
        return new_page()

    def draw_section_title(title: str, current_y: float) -> float:
        current_y = ensure_space(current_y, 0.4 * inch)
        pdf.setFillColorRGB(0.14, 0.25, 0.56)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(left, current_y, title)
        return current_y - 0.22 * inch

    def draw_wrapped_text(text: str, x: float, current_y: float, limit: int = 88, line_gap: float = 0.18 * inch) -> float:
        pdf.setFillColorRGB(0.12, 0.16, 0.25)
        pdf.setFont("Helvetica", 10.5)
        lines = _wrap_text(text, limit=limit)
        current_y = ensure_space(current_y, max(len(lines), 1) * line_gap + 0.04 * inch)
        for line in lines:
            pdf.drawString(x, current_y, line)
            current_y -= line_gap
        return current_y

    def draw_key_value_rows(title: str, rows: list[tuple[str, str]], current_y: float) -> float:
        current_y = draw_section_title(title, current_y)
        row_height = 0.24 * inch
        current_y = ensure_space(current_y, len(rows) * row_height + 0.1 * inch)
        for label, value in rows:
            pdf.setFont("Helvetica-Bold", 10.5)
            pdf.setFillColorRGB(0.12, 0.16, 0.25)
            pdf.drawString(left, current_y, f"{label}:")
            pdf.setFont("Helvetica", 10.5)
            pdf.drawString(left + 1.9 * inch, current_y, value)
            current_y -= row_height
        return current_y - 0.08 * inch

    def draw_simple_table(
        title: str,
        headers: list[str],
        rows: list[list[str]],
        current_y: float,
        col_widths: list[float],
        row_height: float = 0.28 * inch,
        font_size: float = 8.5,
    ) -> float:
        current_y = draw_section_title(title, current_y)
        table_width = sum(col_widths)
        header_height = 0.32 * inch

        def draw_header(y: float) -> float:
            pdf.setFillColorRGB(0.91, 0.94, 0.99)
            pdf.rect(left, y - header_height + 0.04 * inch, table_width, header_height, stroke=0, fill=1)
            pdf.setFillColorRGB(0.12, 0.16, 0.25)
            pdf.setFont("Helvetica-Bold", font_size)
            x = left + 0.06 * inch
            for index, header in enumerate(headers):
                pdf.drawString(x, y - 0.16 * inch, header)
                x += col_widths[index]
            return y - header_height

        current_y = ensure_space(current_y, header_height + row_height)
        current_y = draw_header(current_y)
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColorRGB(0.12, 0.16, 0.25)

        if not rows:
            current_y = ensure_space(current_y, row_height)
            pdf.drawString(left + 0.06 * inch, current_y - 0.16 * inch, "No data available.")
            return current_y - row_height - 0.08 * inch

        for row in rows:
            current_y = ensure_space(current_y, row_height)
            if current_y == top:
                current_y = draw_header(current_y)
                pdf.setFont("Helvetica", font_size)
                pdf.setFillColorRGB(0.12, 0.16, 0.25)

            x = left + 0.06 * inch
            for index, cell in enumerate(row):
                pdf.drawString(x, current_y - 0.16 * inch, str(cell)[:28])
                x += col_widths[index]
            pdf.setStrokeColorRGB(0.86, 0.89, 0.94)
            pdf.line(left, current_y - row_height + 0.04 * inch, left + table_width, current_y - row_height + 0.04 * inch)
            current_y -= row_height

        return current_y - 0.08 * inch

    def fmt_mark(value: float | int | None) -> str:
        if value is None:
            return "-"
        numeric = float(value)
        if numeric <= 0:
            return "-"
        if numeric.is_integer():
            return str(int(numeric))
        return f"{numeric:.2f}".rstrip("0").rstrip(".")

    risk_level = prediction.risk_level or "Low"
    risk_score = max(0.0, min(float(prediction.risk_score or 0), 1.0))
    recommendations = prediction.recommendations or []
    feature_importance = prediction.feature_importance or []
    risk_color = {
        "Safe": (0.17, 0.49, 0.32),
        "Low": (0.16, 0.41, 0.68),
        "Medium": (0.83, 0.52, 0.06),
        "High": (0.74, 0.15, 0.15),
    }.get(risk_level, (0.16, 0.41, 0.68))
    fee_status = "Paid"
    if not student.financial or student.financial.fee_due > 0 or student.financial.payment_delay_days > 0:
        fee_status = "Pending"

    pdf.setTitle(f"Parent Report - {student.name}")
    y = top
    pdf.setFillColorRGB(0.14, 0.25, 0.56)
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(left, y, "Student Progress Report For Parent")
    y -= 0.24 * inch
    pdf.setFillColorRGB(0.35, 0.4, 0.5)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(left, y, "Detailed summary prepared from the latest AI retention analysis and student performance data")
    y -= 0.32 * inch

    student_rows = [
        ("Student Name", student.name),
        ("Registration Number", student.registration_number),
        ("Student Email", student.email or "-"),
        ("Student Mobile", student.student_mobile or "-"),
        ("Parent Mobile", student.parent_mobile or "-"),
        ("Counselor", student.counselor_name or "Not Assigned"),
        ("Section", student.section or "-"),
        ("Gender", student.gender or "-"),
        ("Age", str(student.age) if student.age is not None else "-"),
        ("Year", str(student.year)),
        ("Department", student.department),
        ("Career Interest", student.career_interest or "-"),
        ("Skills", student.skills or "-"),
        ("Risk Level", risk_level),
        ("Risk Score", f"{risk_score * 100:.1f}%"),
    ]
    y = draw_key_value_rows("Student Summary", student_rows, y)

    academic_rows = [
        ("Overall Attendance", f"{student.attendance:.0f}%"),
        ("CGPA", f"{student.gpa:.2f}"),
        ("Overall Marks", fmt_mark(student.marks)),
        ("Fee Status", fee_status),
        ("Fee Due", fmt_mark(student.financial.fee_due if student.financial else 0)),
        ("Payment Delay Days", str(student.financial.payment_delay_days if student.financial else 0)),
        ("Scholarship Amount", fmt_mark(student.financial.scholarship_amount if student.financial else 0)),
    ]
    y = draw_key_value_rows("Academic And Financial Summary", academic_rows, y)

    engagement_rows = [
        ("CodeChef Username", student.codechef_username or "-"),
        ("CodeChef Contests", str(student.codechef_contests_participated or 0)),
        ("CodeChef Problems Solved", str(student.codechef_problems_solved or 0)),
        ("CodeChef Participation Status", student.codechef_participation_status or "Not Available"),
        ("Last CodeChef Sync", student.codechef_last_synced_at.strftime("%d %b %Y, %I:%M %p") if student.codechef_last_synced_at else "-"),
    ]
    y = draw_key_value_rows("Engagement And Coding Activity", engagement_rows, y)

    y = draw_section_title("What This Means", y)
    y = draw_wrapped_text(
        prediction.explanation or "The latest analysis suggests the student needs steady academic follow-up and support.",
        left,
        y,
    )
    y -= 0.08 * inch

    if recommendations:
        y = draw_section_title("Suggested Support From Home", y)
        for index, item in enumerate(recommendations, start=1):
            y = draw_wrapped_text(f"{index}. {item}", left + 0.12 * inch, y, limit=84)
            y -= 0.02 * inch

    if feature_importance:
        factor_rows = []
        for item in feature_importance:
            feature_name = str(item.get("feature", "")).replace("num__", "").replace("cat__", "").replace("_", " ").title()
            actual_value = item.get("actual_value")
            factor_rows.append([
                feature_name,
                "-" if actual_value in (None, "") else str(actual_value),
                f"{float(item.get('importance', 0)):.4f}",
            ])
        y = draw_simple_table(
            "Important Factors Observed",
            ["Factor", "Actual Value", "Importance"],
            factor_rows,
            y,
            [2.7 * inch, 1.7 * inch, 1.2 * inch],
            row_height=0.3 * inch,
            font_size=8.6,
        )

    lms_rows = [
        ["Weekly Logins", str(student.lms_activity.weekly_logins if student.lms_activity else 0)],
        ["Average Time Spent", fmt_mark(student.lms_activity.avg_time_spent if student.lms_activity else 0)],
        ["Assignment Submission Rate", f"{(student.lms_activity.assignment_submission_rate if student.lms_activity else 0):.0f}%"],
        ["Missed Assignments", str(student.lms_activity.missed_assignments if student.lms_activity else 0)],
    ]
    y = draw_simple_table(
        "All LMS Activity",
        ["Metric", "Value"],
        lms_rows,
        y,
        [3.2 * inch, 2.6 * inch],
        row_height=0.32 * inch,
        font_size=9.5,
    )

    overall_marks_rows = [[
        fmt_mark(student.pre_t1_marks),
        fmt_mark(student.t1_marks),
        fmt_mark(student.t2_marks),
        fmt_mark(student.t3_marks),
        fmt_mark(student.t4_marks),
        fmt_mark(student.t5_marks),
        fmt_mark(student.marks),
    ]]
    y = draw_simple_table(
        "All Marks Summary",
        ["Pre T1", "T1", "T2", "T3", "T4", "T5", "Overall"],
        overall_marks_rows,
        y,
        [0.8 * inch, 0.65 * inch, 0.65 * inch, 0.65 * inch, 0.65 * inch, 0.65 * inch, 0.85 * inch],
        row_height=0.32 * inch,
        font_size=8.5,
    )

    subject_rows = [
        [
            item.subject_name,
            f"{item.attendance_percentage:.0f}%",
            fmt_mark(item.pre_t1_marks),
            fmt_mark(item.t1_marks),
            fmt_mark(item.t2_marks),
            fmt_mark(item.t3_marks),
            fmt_mark(item.t4_marks),
            fmt_mark(item.t5_marks),
            fmt_mark(item.total_marks),
        ]
        for item in student.subject_attendance
    ]
    y = draw_simple_table(
        "All Subject Wise Attendance And Marks",
        ["Subject", "Att%", "Pre T1", "T1", "T2", "T3", "T4", "T5", "Total"],
        subject_rows,
        y,
        [1.65 * inch, 0.5 * inch, 0.52 * inch, 0.42 * inch, 0.42 * inch, 0.42 * inch, 0.42 * inch, 0.42 * inch, 0.5 * inch],
        row_height=0.27 * inch,
        font_size=6.9,
    )

    assignment_rows = [
        [
            item.subject_name,
            fmt_mark(item.t5_assignment_1),
            fmt_mark(item.t5_assignment_2),
            fmt_mark(item.t5_assignment_3),
            fmt_mark(item.t5_assignment_4),
        ]
        for item in student.subject_attendance
    ]
    y = draw_simple_table(
        "T5 Assignment Marks By Subject",
        ["Subject", "CLA 1", "CLA 2", "CLA 3", "CLA 4"],
        assignment_rows,
        y,
        [2.45 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch, 0.8 * inch],
        row_height=0.28 * inch,
        font_size=8.2,
    )

    y = ensure_space(y, 0.3 * inch)
    pdf.setFillColorRGB(0.38, 0.43, 0.53)
    pdf.setFont("Helvetica", 9)
    pdf.drawString(left, y, "This report is meant to support a constructive parent conversation and should be handled confidentially.")

    pdf.save()
    buffer.seek(0)
    return buffer
