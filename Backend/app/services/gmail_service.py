
import base64
import json
import os

from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


BASE_DIR = Path(__file__).resolve().parents[2]
TOKEN_FILE = BASE_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


def get_gmail_service():
    token_json = os.getenv("GMAIL_TOKEN_JSON")

    if token_json:
        # Production: load credentials from environment variable
        try:
            token_data = json.loads(token_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GMAIL_TOKEN_JSON contains invalid JSON."
            ) from exc

        credentials = Credentials.from_authorized_user_info(
            token_data,
            SCOPES
        )

        using_environment = True

    else:
        # Local development: use token.json
        if os.getenv("VERCEL"):
            raise RuntimeError(
                "GMAIL_TOKEN_JSON is not configured in Vercel."
            )

        if not TOKEN_FILE.exists():
            raise FileNotFoundError(
                f"Gmail OAuth token not found: {TOKEN_FILE}"
            )

        credentials = Credentials.from_authorized_user_file(
            str(TOKEN_FILE),
            SCOPES
        )

        using_environment = False

    # Refresh an expired OAuth access token
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        # Save refreshed credentials only during local development
        if not using_environment:
            TOKEN_FILE.write_text(
                credentials.to_json(),
                encoding="utf-8"
            )
            TOKEN_FILE.chmod(0o600)

    if not credentials.valid:
        raise RuntimeError(
            "Gmail OAuth credentials are invalid. "
            "Check the refresh token and reauthorise if necessary."
        )

    return build(
        "gmail",
        "v1",
        credentials=credentials
    )


def send_email(
    to_email: str,
    subject: str,
    message: str
):
    email = EmailMessage()

    email["To"] = to_email
    email["Subject"] = subject
    email.set_content(message)

    raw_message = base64.urlsafe_b64encode(
        email.as_bytes()
    ).decode("utf-8")

    gmail_service = get_gmail_service()

    result = (
        gmail_service.users()
        .messages()
        .send(
            userId="me",
            body={"raw": raw_message}
        )
        .execute()
    )

    return {
        "message_id": result.get("id"),
        "thread_id": result.get("threadId")
    }
