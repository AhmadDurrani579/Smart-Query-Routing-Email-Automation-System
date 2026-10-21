
from getpass import getpass

from app.services.gmail_service import send_email


def main():
    recipient = input(
        "Enter recipient email address: "
    ).strip()

    if not recipient or "@" not in recipient:
        raise ValueError("Enter a valid recipient address")

    result = send_email(
        to_email=recipient,
        subject="Smart Query Routing System - Gmail API Test",
        message=(
            "Hello,\n\n"
            "This is a test email sent from the "
            "Smart Query Routing System using "
            "the Gmail API.\n\n"
            "Regards,\n"
            "Smart Query Routing System"
        )
    )

    print("Gmail accepted the message!")
    print("Message ID:", result["message_id"])
    print("Thread ID:", result["thread_id"])


if __name__ == "__main__":
    main()
