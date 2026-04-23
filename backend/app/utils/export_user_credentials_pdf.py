from __future__ import annotations

import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.models.user import User
from app.services.report_service import generate_user_credentials_report

DEFAULT_OUTPUT = Path("/Users/karthi/Sample Data/Sample data/user-credentials-report.pdf")


def export_user_credentials_pdf(output_path: Path = DEFAULT_OUTPUT) -> Path:
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.role.asc(), User.name.asc(), User.email.asc()).all()
        pdf_buffer = generate_user_credentials_report(users)
    finally:
        db.close()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_buffer.getvalue())
    return output_path


if __name__ == "__main__":
    cli_output = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_OUTPUT
    created_path = export_user_credentials_pdf(cli_output)
    print(created_path)
