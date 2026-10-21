
import base64

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
    credentials = Credentials.from_authorized_user_file(
        str(TOKEN_FILE),
        SCOPES
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        TOKEN_FILE.write_text(credentials.to_json())
        TOKEN_FILE.chmod(0o600)

    if not credentials.valid:
        raise RuntimeError(
            "Gmail OAuth credentials are invalid. "
            "Reauthorise the Gmail account."
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
