from __future__ import annotations

import ssl
from email.message import EmailMessage

import aiosmtplib
import certifi

from app.core.config import settings


PLACEHOLDER_SMTP_VALUES = {"", "your-email@gmail.com", "your-app-password"}


def _smtp_is_configured() -> bool:
    return (
        settings.SMTP_USERNAME not in PLACEHOLDER_SMTP_VALUES
        and settings.SMTP_PASSWORD not in PLACEHOLDER_SMTP_VALUES
        and settings.SMTP_FROM_EMAIL not in PLACEHOLDER_SMTP_VALUES
    )


def _build_tls_context() -> ssl.SSLContext | None:
    if not settings.SMTP_START_TLS:
        return None
    if settings.SMTP_VALIDATE_CERTS:
        return ssl.create_default_context(cafile=certifi.where())
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _subject_for_risk(risk_level: str) -> str:
    if risk_level == "High":
        return "Important Academic Support Alert: Immediate Attention Needed"
    if risk_level == "Medium":
        return "Academic Support Alert: Please Review Your Current Status"
    return "Academic Progress Update"


def _intro_for_risk(risk_level: str) -> str:
    if risk_level == "High":
        return (
            "You are receiving this email because the student retention system identified a high-priority academic support concern. "
            "This is not a punishment notice. It is an early intervention alert asking you to take immediate academic support action."
        )
    if risk_level == "Medium":
        return (
            "You are receiving this email because the student retention system identified an academic pattern that needs attention. "
            "This is an early support alert to help you act before the issue becomes more serious."
        )
    return (
        "You are receiving this email because the student retention system generated an academic progress update "
        "based on your current performance data."
    )


def _action_label_for_risk(risk_level: str) -> str:
    if risk_level == "High":
        return "Immediate actions recommended"
    if risk_level == "Medium":
        return "Priority actions recommended"
    return "Recommended actions"


def _banner_colors(risk_level: str) -> tuple[str, str]:
    if risk_level == "High":
        return "#b91c1c", "#fef2f2"
    if risk_level == "Medium":
        return "#b45309", "#fffbeb"
    return "#166534", "#f0fdf4"


def _risk_label_bg(risk_level: str) -> tuple[str, str]:
    if risk_level == "High":
        return "#fee2e2", "#991b1b"
    if risk_level == "Medium":
        return "#fef3c7", "#92400e"
    return "#dcfce7", "#166534"


def _build_plain_text(student_name: str, risk_level: str, explanation: str, recommendations: list[str]) -> str:
    return _build_plain_text_with_subjects(student_name, risk_level, explanation, recommendations, [])


def _build_plain_text_with_subjects(
    student_name: str,
    risk_level: str,
    explanation: str,
    recommendations: list[str],
    weak_subject_attendance: list[tuple[str, float]],
) -> str:
    weak_subject_block = (
        [
            "",
            "Subject-wise attendance requiring attention:",
            *[f"- {subject}: {attendance:.0f}%" for subject, attendance in weak_subject_attendance],
        ]
        if weak_subject_attendance
        else []
    )
    return "\n".join(
        [
            f"Hello {student_name},",
            "",
            "Reason for this email:",
            "This email was sent automatically after the student retention system reviewed your academic, attendance, and LMS activity data.",
            "",
            _intro_for_risk(risk_level),
            "",
            f"Risk Level: {risk_level}",
            f"Reason: {explanation}",
            *weak_subject_block,
            "",
            f"{_action_label_for_risk(risk_level)}:",
            *[f"- {item}" for item in recommendations],
            "",
            "Please contact your faculty counselor as soon as possible for support.",
            "",
            "Predictive Analytics for Student Retention",
        ]
    )


def _build_html(
    student_name: str,
    student_email: str,
    risk_level: str,
    explanation: str,
    recommendations: list[str],
    weak_subject_attendance: list[tuple[str, float]],
) -> str:
    banner_text, banner_bg = _banner_colors(risk_level)
    pill_bg, pill_text = _risk_label_bg(risk_level)
    recommendation_items = "".join(
        f"""
        <tr>
          <td style="padding:0 0 14px 0;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
              <tr>
                <td style="width:18px;vertical-align:top;padding-top:4px;">
                  <span style="display:inline-block;width:10px;height:10px;border-radius:999px;background:{banner_text};"></span>
                </td>
                <td style="font-size:15px;line-height:1.75;color:#334155;">
                  {item}
                </td>
              </tr>
            </table>
          </td>
        </tr>
        """
        for item in recommendations
    )
    weak_subject_items = "".join(
        f"""
        <tr>
          <td style="padding:0 0 12px 0;font-size:14px;color:#64748b;width:220px;">{subject}</td>
          <td style="padding:0 0 12px 0;font-size:14px;color:#b91c1c;font-weight:800;">{attendance:.0f}%</td>
        </tr>
        """
        for subject, attendance in weak_subject_attendance
    )
    weak_subject_section = (
        f"""
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 24px 0;">
          <tr>
            <td style="padding:22px;background:#fef2f2;border:1px solid #fecaca;border-radius:22px;">
              <div style="font-size:13px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#b91c1c;">Subject-Wise Attendance Concern</div>
              <p style="margin:12px 0 16px 0;font-size:15px;line-height:1.8;color:#7f1d1d;">
                The following subjects currently have attendance below 75% and need immediate attention.
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                {weak_subject_items}
              </table>
            </td>
          </tr>
        </table>
        """
        if weak_subject_attendance
        else ""
    )
    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body style="margin:0;padding:0;background:#eef3f8;font-family:Arial,sans-serif;color:#0f172a;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:linear-gradient(180deg,#eef3f8 0%,#f8fafc 100%);padding:28px 12px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:720px;background:#ffffff;border-radius:28px;overflow:hidden;box-shadow:0 18px 50px rgba(15,23,42,0.12);">
                <tr>
                  <td style="padding:32px;background:linear-gradient(135deg,{banner_bg} 0%,#ffffff 100%);border-bottom:1px solid #e2e8f0;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                      <tr>
                        <td style="vertical-align:top;">
                          <div style="font-size:12px;letter-spacing:0.24em;text-transform:uppercase;color:{banner_text};font-weight:800;">Student Retention Alert</div>
                          <h1 style="margin:14px 0 0 0;font-size:30px;line-height:1.15;color:#0f172a;font-weight:800;">{risk_level} Risk Notification</h1>
                          <p style="margin:12px 0 0 0;font-size:15px;line-height:1.7;color:#475569;max-width:470px;">
                            Personalized AI-driven outreach for student support, intervention, and follow-up.
                          </p>
                        </td>
                        <td align="right" style="vertical-align:top;">
                          <span style="display:inline-block;padding:10px 16px;border-radius:999px;background:{pill_bg};color:{pill_text};font-size:13px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;">
                            {risk_level} Risk
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:34px 32px 18px 32px;">
                    <p style="margin:0 0 16px 0;font-size:17px;line-height:1.7;color:#0f172a;">Hello <strong>{student_name}</strong>,</p>
                    <p style="margin:0 0 24px 0;font-size:16px;line-height:1.8;color:#334155;">{_intro_for_risk(risk_level)}</p>

                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 24px 0;">
                      <tr>
                        <td style="padding:22px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:22px;">
                          <div style="font-size:13px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#64748b;">Student Details</div>
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:16px;">
                            <tr>
                              <td style="padding:0 0 12px 0;font-size:14px;color:#64748b;width:140px;">Student Name</td>
                              <td style="padding:0 0 12px 0;font-size:14px;color:#0f172a;font-weight:700;">{student_name}</td>
                            </tr>
                            <tr>
                              <td style="padding:0 0 12px 0;font-size:14px;color:#64748b;width:140px;">Student Email</td>
                              <td style="padding:0 0 12px 0;font-size:14px;color:#0f172a;font-weight:700;">{student_email}</td>
                            </tr>
                            <tr>
                              <td style="padding:0;font-size:14px;color:#64748b;width:140px;">Risk Status</td>
                              <td style="padding:0;font-size:14px;color:{banner_text};font-weight:800;">{risk_level}</td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </table>

                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 24px 0;">
                      <tr>
                        <td style="padding:22px;background:#fff7ed;border:1px solid #fed7aa;border-radius:22px;">
                          <div style="font-size:13px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#c2410c;">Why You Received This</div>
                          <p style="margin:14px 0 0 0;font-size:15px;line-height:1.8;color:#7c2d12;">
                            This email was sent automatically after the student retention system reviewed your academic,
                            attendance, and LMS activity data.
                          </p>
                          <p style="margin:14px 0 0 0;font-size:15px;line-height:1.8;color:#7c2d12;">{explanation}</p>
                        </td>
                      </tr>
                    </table>

                    {weak_subject_section}

                    <div style="margin:0 0 14px 0;font-size:20px;font-weight:800;color:#0f172a;">{_action_label_for_risk(risk_level)}</div>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 26px 0;">
                      {recommendation_items}
                    </table>

                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 18px 0;">
                      <tr>
                        <td style="padding:20px 22px;border-radius:22px;background:#eff6ff;border:1px solid #bfdbfe;">
                          <div style="font-size:13px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#1d4ed8;">Next Step</div>
                          <p style="margin:12px 0 0 0;font-size:15px;line-height:1.8;color:#1e3a8a;">
                            Please contact your faculty counselor as soon as possible for support, academic planning, and follow-up actions.
                          </p>
                        </td>
                      </tr>
                    </table>

                    <div style="margin-top:8px;font-size:12px;line-height:1.7;color:#94a3b8;text-align:center;">
                      This email was generated by the Predictive Analytics for Student Retention platform.
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


def _build_follow_up_plain_text(
    student_name: str,
    risk_level: str,
    follow_up_date: str,
    status: str,
    notes: str,
) -> str:
    note_block = f"Faculty Notes: {notes}\n\n" if notes else ""
    return "\n".join(
        [
            f"Hello {student_name},",
            "",
            "This is a follow-up update from the student retention team.",
            "",
            f"Current Risk Level: {risk_level}",
            f"Intervention Status: {status.replace('_', ' ')}",
            f"Next Follow-up Date: {follow_up_date}",
            "",
            note_block.rstrip(),
            "Please be available for the scheduled follow-up and complete any pending academic actions before that date.",
            "",
            "Predictive Analytics for Student Retention",
        ]
    ).replace("\n\n\n", "\n\n")


def _build_follow_up_html(
    student_name: str,
    student_email: str,
    risk_level: str,
    follow_up_date: str,
    status: str,
    notes: str,
) -> str:
    banner_text, banner_bg = _banner_colors(risk_level)
    pill_bg, pill_text = _risk_label_bg(risk_level)
    notes_html = (
        f"""
        <tr>
          <td style="padding:22px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:22px;">
            <div style="font-size:13px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#475569;">Faculty Notes</div>
            <p style="margin:14px 0 0 0;font-size:15px;line-height:1.8;color:#334155;">{notes}</p>
          </td>
        </tr>
        """
        if notes
        else ""
    )
    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body style="margin:0;padding:0;background:#eef3f8;font-family:Arial,sans-serif;color:#0f172a;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:linear-gradient(180deg,#eef3f8 0%,#f8fafc 100%);padding:28px 12px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:720px;background:#ffffff;border-radius:28px;overflow:hidden;box-shadow:0 18px 50px rgba(15,23,42,0.12);">
                <tr>
                  <td style="padding:32px;background:linear-gradient(135deg,{banner_bg} 0%,#ffffff 100%);border-bottom:1px solid #e2e8f0;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                      <tr>
                        <td style="vertical-align:top;">
                          <div style="font-size:12px;letter-spacing:0.24em;text-transform:uppercase;color:{banner_text};font-weight:800;">Follow-up Scheduled</div>
                          <h1 style="margin:14px 0 0 0;font-size:30px;line-height:1.15;color:#0f172a;font-weight:800;">Student Support Follow-up</h1>
                        </td>
                        <td align="right" style="vertical-align:top;">
                          <span style="display:inline-block;padding:10px 16px;border-radius:999px;background:{pill_bg};color:{pill_text};font-size:13px;font-weight:800;letter-spacing:0.08em;text-transform:uppercase;">
                            {risk_level} Risk
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
                <tr>
                  <td style="padding:34px 32px 18px 32px;">
                    <p style="margin:0 0 16px 0;font-size:17px;line-height:1.7;color:#0f172a;">Hello <strong>{student_name}</strong>,</p>
                    <p style="margin:0 0 24px 0;font-size:16px;line-height:1.8;color:#334155;">
                      A follow-up has been scheduled by the student retention team. Please review the details below and be prepared for the next check-in.
                    </p>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 24px 0;">
                      <tr>
                        <td style="padding:22px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:22px;">
                          <div style="font-size:13px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#64748b;">Follow-up Details</div>
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:16px;">
                            <tr><td style="padding:0 0 12px 0;font-size:14px;color:#64748b;width:160px;">Student Name</td><td style="padding:0 0 12px 0;font-size:14px;color:#0f172a;font-weight:700;">{student_name}</td></tr>
                            <tr><td style="padding:0 0 12px 0;font-size:14px;color:#64748b;width:160px;">Student Email</td><td style="padding:0 0 12px 0;font-size:14px;color:#0f172a;font-weight:700;">{student_email}</td></tr>
                            <tr><td style="padding:0 0 12px 0;font-size:14px;color:#64748b;width:160px;">Current Risk</td><td style="padding:0 0 12px 0;font-size:14px;color:{banner_text};font-weight:800;">{risk_level}</td></tr>
                            <tr><td style="padding:0 0 12px 0;font-size:14px;color:#64748b;width:160px;">Intervention Status</td><td style="padding:0 0 12px 0;font-size:14px;color:#0f172a;font-weight:700;">{status.replace('_', ' ')}</td></tr>
                            <tr><td style="padding:0;font-size:14px;color:#64748b;width:160px;">Next Follow-up Date</td><td style="padding:0;font-size:14px;color:#0f172a;font-weight:700;">{follow_up_date}</td></tr>
                          </table>
                        </td>
                      </tr>
                    </table>
                    {notes_html}
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:24px 0 18px 0;">
                      <tr>
                        <td style="padding:20px 22px;border-radius:22px;background:#eff6ff;border:1px solid #bfdbfe;">
                          <div style="font-size:13px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#1d4ed8;">Action Required</div>
                          <p style="margin:12px 0 0 0;font-size:15px;line-height:1.8;color:#1e3a8a;">
                            Please complete any pending academic work and be available for the scheduled follow-up discussion before or on {follow_up_date}.
                          </p>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """


async def send_risk_alert_email(
    student_name: str,
    student_email: str,
    risk_level: str,
    explanation: str,
    recommendations: list[str],
    weak_subject_attendance: list[tuple[str, float]] | None = None,
) -> dict[str, str]:
    if not _smtp_is_configured():
        return {"status": "skipped", "detail": "SMTP is not configured"}
    weak_subject_attendance = weak_subject_attendance or []

    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = student_email
    message["Subject"] = _subject_for_risk(risk_level)
    message.set_content(_build_plain_text_with_subjects(student_name, risk_level, explanation, recommendations, weak_subject_attendance))
    message.add_alternative(
        _build_html(student_name, student_email, risk_level, explanation, recommendations, weak_subject_attendance),
        subtype="html",
    )

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        start_tls=settings.SMTP_START_TLS,
        tls_context=_build_tls_context(),
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    )
    return {"status": "sent", "detail": f"Alert email sent to {student_email}"}


async def send_follow_up_email(
    student_name: str,
    student_email: str,
    risk_level: str,
    follow_up_date: str,
    status: str,
    notes: str,
) -> dict[str, str]:
    if not _smtp_is_configured():
        return {"status": "skipped", "detail": "SMTP is not configured"}

    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = student_email
    message["Subject"] = f"Follow-up Scheduled: {follow_up_date}"
    message.set_content(_build_follow_up_plain_text(student_name, risk_level, follow_up_date, status, notes))
    message.add_alternative(
        _build_follow_up_html(student_name, student_email, risk_level, follow_up_date, status, notes),
        subtype="html",
    )

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        start_tls=settings.SMTP_START_TLS,
        tls_context=_build_tls_context(),
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    )
    return {"status": "sent", "detail": f"Follow-up email sent to {student_email}"}


async def send_resolution_email(
    student_name: str,
    student_email: str,
    risk_level: str,
    notes: str,
) -> dict[str, str]:
    if not _smtp_is_configured():
        return {"status": "skipped", "detail": "SMTP is not configured"}

    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = student_email
    message["Subject"] = "Resolution Update: Student Support Case Closed"

    plain_text = "\n".join(
        [
            f"Hello {student_name},",
            "",
            "This is to inform you that your current intervention case has been marked as resolved by the student retention team.",
            "",
            f"Latest Risk Level: {risk_level}",
            "",
            f"Faculty Notes: {notes}" if notes else "No additional notes were recorded.",
            "",
            "Please continue maintaining your academic progress and stay in contact with your faculty mentor if you need further support.",
            "",
            "Predictive Analytics for Student Retention",
        ]
    )

    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body style="margin:0;padding:0;background:#eef7f1;font-family:Arial,sans-serif;color:#0f172a;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:28px 12px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:720px;background:#ffffff;border-radius:28px;overflow:hidden;box-shadow:0 18px 50px rgba(15,23,42,0.12);">
                <tr>
                  <td style="padding:32px;background:linear-gradient(135deg,#dcfce7 0%,#ffffff 100%);border-bottom:1px solid #e2e8f0;">
                    <div style="font-size:12px;letter-spacing:0.24em;text-transform:uppercase;color:#166534;font-weight:800;">Intervention Resolved</div>
                    <h1 style="margin:14px 0 0 0;font-size:30px;line-height:1.15;color:#0f172a;font-weight:800;">Your support case has been resolved</h1>
                    <p style="margin:12px 0 0 0;font-size:15px;line-height:1.7;color:#475569;">
                      This update confirms that your current intervention case is now marked as resolved.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:34px 32px 24px 32px;">
                    <p style="margin:0 0 18px 0;font-size:17px;line-height:1.7;color:#0f172a;">Hello <strong>{student_name}</strong>,</p>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 22px 0;">
                      <tr>
                        <td style="padding:22px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:22px;">
                          <div style="font-size:13px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#64748b;">Resolution Details</div>
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:16px;">
                            <tr><td style="padding:0 0 12px 0;font-size:14px;color:#64748b;width:160px;">Student Name</td><td style="padding:0 0 12px 0;font-size:14px;color:#0f172a;font-weight:700;">{student_name}</td></tr>
                            <tr><td style="padding:0 0 12px 0;font-size:14px;color:#64748b;width:160px;">Student Email</td><td style="padding:0 0 12px 0;font-size:14px;color:#0f172a;font-weight:700;">{student_email}</td></tr>
                            <tr><td style="padding:0;font-size:14px;color:#64748b;width:160px;">Latest Risk Level</td><td style="padding:0;font-size:14px;color:#166534;font-weight:800;">{risk_level}</td></tr>
                          </table>
                        </td>
                      </tr>
                    </table>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:0 0 22px 0;">
                      <tr>
                        <td style="padding:22px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:22px;">
                          <div style="font-size:13px;font-weight:800;letter-spacing:0.16em;text-transform:uppercase;color:#166534;">Faculty Notes</div>
                          <p style="margin:14px 0 0 0;font-size:15px;line-height:1.8;color:#166534;">{notes if notes else "No additional notes were recorded."}</p>
                        </td>
                      </tr>
                    </table>
                    <p style="margin:0;font-size:15px;line-height:1.8;color:#334155;">
                      Please continue maintaining your academic progress. If you need further support later, stay in contact with your faculty mentor.
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    message.set_content(plain_text)
    message.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        start_tls=settings.SMTP_START_TLS,
        tls_context=_build_tls_context(),
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    )
    return {"status": "sent", "detail": f"Resolution email sent to {student_email}"}


async def send_password_reset_otp_email(
    user_name: str,
    user_email: str,
    otp_code: str,
) -> dict[str, str]:
    if not _smtp_is_configured():
        return {"status": "skipped", "detail": "SMTP is not configured"}

    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = user_email
    message["Subject"] = "Password Reset OTP"

    plain_text = "\n".join(
        [
            f"Hello {user_name},",
            "",
            "You requested a password reset for the Student Retention platform.",
            f"Your OTP is: {otp_code}",
            "This OTP is valid for 3 minutes.",
            "",
            "If you did not request this reset, please ignore this email.",
        ]
    )

    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body style="margin:0;padding:0;background:#eef3f8;font-family:Arial,sans-serif;color:#0f172a;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:28px 12px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border-radius:28px;overflow:hidden;box-shadow:0 18px 50px rgba(15,23,42,0.12);">
                <tr>
                  <td style="padding:32px;background:linear-gradient(135deg,#eff6ff 0%,#ffffff 100%);border-bottom:1px solid #e2e8f0;">
                    <div style="font-size:12px;letter-spacing:0.24em;text-transform:uppercase;color:#1d4ed8;font-weight:800;">Password Recovery</div>
                    <h1 style="margin:14px 0 0 0;font-size:30px;line-height:1.15;color:#0f172a;font-weight:800;">Your OTP for password reset</h1>
                  </td>
                </tr>
                <tr>
                  <td style="padding:32px;">
                    <p style="margin:0 0 18px 0;font-size:16px;line-height:1.8;color:#334155;">Hello <strong>{user_name}</strong>,</p>
                    <p style="margin:0 0 22px 0;font-size:15px;line-height:1.8;color:#475569;">Use the one-time password below to reset your login password. This OTP is valid for 3 minutes.</p>
                    <div style="margin:0 0 22px 0;padding:18px 22px;border-radius:22px;background:#f8fafc;border:1px solid #dbeafe;text-align:center;">
                      <div style="font-size:12px;letter-spacing:0.22em;text-transform:uppercase;color:#64748b;font-weight:800;">One-Time Password</div>
                      <div style="margin-top:12px;font-size:34px;letter-spacing:0.28em;font-weight:800;color:#0f172a;">{otp_code}</div>
                    </div>
                    <p style="margin:0;font-size:14px;line-height:1.8;color:#64748b;">If you did not request this reset, you can ignore this email.</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    message.set_content(plain_text)
    message.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        start_tls=settings.SMTP_START_TLS,
        tls_context=_build_tls_context(),
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    )
    return {"status": "sent", "detail": f"OTP email sent to {user_email}"}


async def send_security_grid_reset_otp_email(
    user_name: str,
    user_email: str,
    otp_code: str,
) -> dict[str, str]:
    if not _smtp_is_configured():
        return {"status": "skipped", "detail": "SMTP is not configured"}

    message = EmailMessage()
    message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
    message["To"] = user_email
    message["Subject"] = "Security Grid Reset OTP"

    plain_text = "\n".join(
        [
            f"Hello {user_name},",
            "",
            "You requested a security grid reset for the Student Retention platform.",
            f"Your OTP is: {otp_code}",
            "This OTP is valid for 3 minutes.",
            "",
            "After verification, a new personal grid will be generated for your account.",
            "If you did not request this reset, please ignore this email.",
        ]
    )

    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body style="margin:0;padding:0;background:#eef3f8;font-family:Arial,sans-serif;color:#0f172a;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:28px 12px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;background:#ffffff;border-radius:28px;overflow:hidden;box-shadow:0 18px 50px rgba(15,23,42,0.12);">
                <tr>
                  <td style="padding:32px;background:linear-gradient(135deg,#eef2ff 0%,#ffffff 100%);border-bottom:1px solid #e2e8f0;">
                    <div style="font-size:12px;letter-spacing:0.24em;text-transform:uppercase;color:#31489d;font-weight:800;">Security Grid Reset</div>
                    <h1 style="margin:14px 0 0 0;font-size:30px;line-height:1.15;color:#0f172a;font-weight:800;">Your OTP for grid reset</h1>
                  </td>
                </tr>
                <tr>
                  <td style="padding:32px;">
                    <p style="margin:0 0 18px 0;font-size:16px;line-height:1.8;color:#334155;">Hello <strong>{user_name}</strong>,</p>
                    <p style="margin:0 0 22px 0;font-size:15px;line-height:1.8;color:#475569;">Use the one-time password below to securely generate a brand-new personal grid for your account. This OTP is valid for 3 minutes.</p>
                    <div style="margin:0 0 22px 0;padding:18px 22px;border-radius:22px;background:#f8fafc;border:1px solid #dbeafe;text-align:center;">
                      <div style="font-size:12px;letter-spacing:0.22em;text-transform:uppercase;color:#64748b;font-weight:800;">One-Time Password</div>
                      <div style="margin-top:12px;font-size:34px;letter-spacing:0.28em;font-weight:800;color:#0f172a;">{otp_code}</div>
                    </div>
                    <p style="margin:0;font-size:14px;line-height:1.8;color:#64748b;">If you did not request this grid reset, you can ignore this email.</p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """

    message.set_content(plain_text)
    message.add_alternative(html, subtype="html")

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USERNAME,
        password=settings.SMTP_PASSWORD,
        start_tls=settings.SMTP_START_TLS,
        tls_context=_build_tls_context(),
        timeout=settings.SMTP_TIMEOUT_SECONDS,
    )
    return {"status": "sent", "detail": f"OTP email sent to {user_email}"}
