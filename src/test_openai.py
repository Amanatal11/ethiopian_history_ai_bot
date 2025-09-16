import os
import sys
from dotenv import load_dotenv
from langchain_community.chat_models import ChatGroq

load_dotenv()


def _get_api_key() -> str:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key or key.upper().startswith("REPLACE_"):
        print("ERROR: GROQ_API_KEY is missing or is a placeholder. Set it in .env.")
        sys.exit(1)
    return key


def test_openai() -> None:
    _get_api_key()
    try:
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        from langchain.schema import HumanMessage
        resp = llm.invoke([HumanMessage(content="Hello, test Ethiopian history agent (Groq).")])
        print(resp.content)
    except Exception as exc:
        print(f"ERROR: Groq API call failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    test_openai()
