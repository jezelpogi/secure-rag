"""Central settings: paths, model names, retrieval size, and role permissions."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = Path("data/docs")
DB_DIR = "chroma_db"
AUDIT_LOG = Path("logs/audit.jsonl")

MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")  # set LLM_MODEL in .env to change
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
K = 5
CHUNK_MIN_CHARS = 400

# Which document departments each role may search. Enforced at retrieval time.
ROLE_ACCESS = {
    "employee": ["public"],
    "hr": ["public", "hr"],
    "finance": ["public", "finance"],
    "engineering": ["public", "engineering"],
    "admin": ["public", "hr", "finance", "engineering"],
}
