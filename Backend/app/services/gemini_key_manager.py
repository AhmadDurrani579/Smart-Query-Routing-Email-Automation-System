
from google import genai
from google.genai.errors import ServerError

from app.core.config import settings
from google.genai import errors


class GeminiKeyManager:
    def __init__(self):
        self.keys = settings.GEMINI_API_KEYS

        if not self.keys:
            raise ValueError(
                "No Gemini API keys configured"
            )


    def generate_content(self, **kwargs):
        last_error = None

        for key in self.keys:
            try:
                with genai.Client(api_key=key) as client:
                    return client.models.generate_content(
                        **kwargs
                    )

            except ServerError as error:
                last_error = error

                # 503 means Gemini is temporarily
                # unavailable or experiencing high demand.
                # Do not switch API keys.
                # Let the classification worker retry later.
                if error.code == 503:
                    raise

                # Other temporary server errors may
                # use an independently configured backup.
                if error.code in (500, 502, 504):
                    continue

                # Unexpected server error
                raise

        if last_error is not None:
            raise last_error

        raise RuntimeError(
            "Gemini request could not be completed"
        )
