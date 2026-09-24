"""Shared heavyweight objects: embedding model, vector store client, and LLM client."""
import anthropic
import chromadb
from sentence_transformers import SentenceTransformer

from settings import DB_DIR, EMBEDDING_MODEL

embedder = SentenceTransformer(EMBEDDING_MODEL)
llm = anthropic.Anthropic()
db = chromadb.PersistentClient(path=DB_DIR)


def get_collection():
    return db.get_or_create_collection("docs")
