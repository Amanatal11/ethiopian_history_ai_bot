import os
import sys
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()


def _prepare_embeddings():
    # Local embeddings, no API key required
    model_name = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    return HuggingFaceEmbeddings(model_name=model_name)


def build_vector_db():
    print("📖 Loading documents...")
    loader = DirectoryLoader("data", glob="*.txt", loader_cls=TextLoader)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)

    print(f"✅ Split into {len(texts)} chunks.")

    embeddings = _prepare_embeddings()
    db = FAISS.from_documents(texts, embeddings)
    db.save_local("vectorstore")

    print("✅ Vector DB saved at ./vectorstore")

if __name__ == "__main__":
    build_vector_db()
