from __future__ import annotations

import json
import ssl
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib import error, parse, request

from fastapi import HTTPException, status
import certifi
from jose import jwt

from app.core.config import settings

TOKEN_URL = "https://oauth2.googleapis.com/token"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"


def upload_pdf_report_to_drive(pdf_bytes: bytes, filename: str) -> str:
    if not settings.GOOGLE_DRIVE_REPORT_FOLDER_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Drive report folder is not configured.",
        )

    credentials = _load_credentials(settings.GOOGLE_DRIVE_CREDENTIALS_FILE)
    access_token = _fetch_access_token(credentials)
    try:
        file_id = _upload_file(
            access_token=access_token,
            folder_id=settings.GOOGLE_DRIVE_REPORT_FOLDER_ID,
            filename=filename,
            content=pdf_bytes,
            mime_type="application/pdf",
        )
    except HTTPException as exc:
        if "File not found" in str(exc.detail):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Google Drive folder is not accessible. Share the Student_retention folder with "
                    "the service account email as Editor, then try again."
                ),
            ) from exc
        raise
    _make_file_public(access_token, file_id)
    return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"


def _load_credentials(path: Path) -> dict[str, str]:
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google Drive credentials file is missing.",
        )
    return json.loads(path.read_text())


def _fetch_access_token(credentials: dict[str, str]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": credentials["client_email"],
        "scope": DRIVE_SCOPE,
        "aud": TOKEN_URL,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    assertion = jwt.encode(payload, credentials["private_key"], algorithm="RS256")
    form_data = parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion,
        }
    ).encode()
    response = _request_json(
        request.Request(
            TOKEN_URL,
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
    )
    return response["access_token"]


def _upload_file(access_token: str, folder_id: str, filename: str, content: bytes, mime_type: str) -> str:
    boundary = f"report-{uuid.uuid4().hex}"
    metadata = {
        "name": filename,
        "mimeType": mime_type,
    }
    if folder_id:
        metadata["parents"] = [folder_id]
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: {mime_type}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()

    url = f"{DRIVE_UPLOAD_URL}?uploadType=multipart&fields=id"
    response = _request_json(
        request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": f"multipart/related; boundary={boundary}",
            },
            method="POST",
        )
    )
    return response["id"]


def _make_file_public(access_token: str, file_id: str) -> None:
    permission = {
        "type": "anyone",
        "role": "reader",
    }
    _request_json(
        request.Request(
            f"{DRIVE_FILES_URL}/{file_id}/permissions",
            data=json.dumps(permission).encode(),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
    )


def _request_json(req: request.Request) -> dict[str, object]:
    try:
        context = ssl.create_default_context(cafile=certifi.where())
        with request.urlopen(req, timeout=30, context=context) as response:
            return json.loads(response.read().decode())
    except error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Google Drive request failed: {detail}",
        ) from exc
    except error.URLError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Google Drive: {exc.reason}",
        ) from exc
