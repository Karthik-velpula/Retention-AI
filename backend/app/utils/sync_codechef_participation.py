from __future__ import annotations

import argparse
import re
import time
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.student import Student
from app.utils.init_db import init_db

PROFILE_URL_TEMPLATE = "https://www.codechef.com/users/{username}"
PARTICIPATED = "Participated"
NOT_PARTICIPATED = "Not Participated"
NOT_AVAILABLE = "Not Available"


def _profile_markers(username: str) -> list[str]:
    return [
        f"/users/{username.lower()}",
        username.lower(),
        "user profile",
        "fully solved",
        "partially solved",
    ]


def _contest_markers() -> list[str]:
    return [
        "contest rating",
        "rating history",
        "global rank",
        "country rank",
        "stars",
        "star rating",
        "rating-data-section",
        "rating-header",
    ]


def _infer_status(username: str, response: httpx.Response) -> str:
    if response.status_code == 404:
        return NOT_AVAILABLE
    if response.status_code >= 400:
        return NOT_AVAILABLE

    html = response.text.lower()
    username_lower = username.lower()

    # CodeChef sometimes serves the marketing home page instead of a valid
    # profile. We only trust the result when the page looks like a user page.
    has_profile_markers = any(marker in html for marker in _profile_markers(username_lower))
    if not has_profile_markers:
        return NOT_AVAILABLE

    if any(marker in html for marker in _contest_markers()):
        return PARTICIPATED

    rating_match = re.search(r"contest rating[^0-9]{0,20}([1-9][0-9]{2,4})", html)
    if rating_match:
        return PARTICIPATED

    stars_match = re.search(r"([1-7])\s*\*|\b([1-7])\s+stars?\b", html)
    if stars_match:
        return PARTICIPATED

    return NOT_PARTICIPATED


def sync_codechef_participation(
    db: Session,
    *,
    limit: int | None = None,
    registration_number: str | None = None,
    delay_seconds: float = 0.2,
    timeout_seconds: float = 15.0,
) -> dict[str, int]:
    query = db.query(Student).filter(Student.codechef_username.is_not(None), Student.codechef_username != "-")
    if registration_number:
        query = query.filter(Student.registration_number == registration_number)
    students = query.order_by(Student.id.asc())
    if limit is not None:
        students = students.limit(limit)
    students = students.all()

    stats = {"processed": 0, "participated": 0, "not_participated": 0, "not_available": 0}

    with httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers={
            "User-Agent": "StudentRetentionBot/1.0 (+CodeChef profile sync for educational analytics)",
        },
    ) as client:
        for student in students:
            username = (student.codechef_username or "").strip()
            if not username or username == "-":
                continue

            status = NOT_AVAILABLE
            try:
                response = client.get(PROFILE_URL_TEMPLATE.format(username=username))
                status = _infer_status(username, response)
            except httpx.HTTPError:
                status = NOT_AVAILABLE

            student.codechef_participation_status = status
            student.codechef_last_synced_at = datetime.utcnow()

            if status == PARTICIPATED:
                stats["participated"] += 1
            elif status == NOT_PARTICIPATED:
                stats["not_participated"] += 1
            else:
                stats["not_available"] += 1
            stats["processed"] += 1

            if delay_seconds > 0:
                time.sleep(delay_seconds)

        db.commit()

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync CodeChef participation status for students with usernames.")
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N students with CodeChef usernames.")
    parser.add_argument("--registration-number", type=str, default=None, help="Only sync one student by registration number.")
    parser.add_argument("--delay-seconds", type=float, default=0.2, help="Delay between profile requests.")
    parser.add_argument("--timeout-seconds", type=float, default=15.0, help="HTTP timeout per profile request.")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        stats = sync_codechef_participation(
            db,
            limit=args.limit,
            registration_number=args.registration_number,
            delay_seconds=args.delay_seconds,
            timeout_seconds=args.timeout_seconds,
        )
    finally:
        db.close()

    print(
        f"Processed {stats['processed']} students: "
        f"{stats['participated']} participated, "
        f"{stats['not_participated']} not participated, "
        f"{stats['not_available']} not available."
    )


if __name__ == "__main__":
    main()
