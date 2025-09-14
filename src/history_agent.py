import os
import sys
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from dotenv import load_dotenv

load_dotenv()


def _require_api_key() -> None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key.upper().startswith("REPLACE_"):
        print("ERROR: OPENAI_API_KEY is missing or is a placeholder. Set it in .env.")
        sys.exit(1)


def run_agent():
    _require_api_key()
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.load_local("vectorstore", embeddings, allow_dangerous_deserialization=True)

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    qa = RetrievalQA.from_chain_type(llm=llm, retriever=db.as_retriever())

    while True:
        query = input("\n❓ Ask about Ethiopian history (or type 'exit'): ")
        if query.lower() in ["exit", "quit"]:
            break
        answer = qa.run(query)
        print(f"\n💡 {answer}\n")

if __name__ == "__main__":
    run_agent()
