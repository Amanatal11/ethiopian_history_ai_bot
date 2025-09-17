import os
import sys
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.chains import RetrievalQA
from dotenv import load_dotenv

load_dotenv()


def _require_api_key() -> None:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key or key.upper().startswith("REPLACE_"):
        print("ERROR: GROQ_API_KEY is missing or is a placeholder. Set it in .env.")
        sys.exit(1)


def run_agent():
    _require_api_key()
    embeddings = FastEmbedEmbeddings(model_name=os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"))
    db = FAISS.load_local("vectorstore", embeddings, allow_dangerous_deserialization=True)

    llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    qa = RetrievalQA.from_chain_type(llm=llm, retriever=db.as_retriever())

    while True:
        query = input("\n❓ Ask about Ethiopian history (or type 'exit'): ")
        if query.lower() in ["exit", "quit"]:
            break
        answer = qa.run(query)
        print(f"\n💡 {answer}\n")

if __name__ == "__main__":
    run_agent()
