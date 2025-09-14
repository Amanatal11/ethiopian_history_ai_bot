import os
import sys
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()


def _require_api_key() -> None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key.upper().startswith("REPLACE_"):
        print("ERROR: OPENAI_API_KEY is missing or is a placeholder. Set it in .env.")
        sys.exit(1)


def build_vector_db():
    _require_api_key()
    print("📖 Loading documents...")
    loader = DirectoryLoader("data", glob="*.txt", loader_cls=TextLoader)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)

    print(f"✅ Split into {len(texts)} chunks.")

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    db = FAISS.from_documents(texts, embeddings)
    db.save_local("vectorstore")

    print("✅ Vector DB saved at ./vectorstore")

if __name__ == "__main__":
    build_vector_db()
