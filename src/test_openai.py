import os
import sys
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


def _get_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key.upper().startswith("REPLACE_"):
        print("ERROR: OPENAI_API_KEY is missing or is a placeholder. Set it in .env.")
        sys.exit(1)
    return key


def test_openai() -> None:
    client = OpenAI(api_key=_get_api_key())
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello, test Ethiopian history agent setup."}],
        )
        print(response.choices[0].message.content)
    except Exception as exc:
        print(f"ERROR: OpenAI API call failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    test_openai()
