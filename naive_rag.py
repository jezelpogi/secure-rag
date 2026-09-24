"""RAG pipeline: role-based retrieval, optional PII redaction, and validated citations."""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from security.pii import Redactor

load_dotenv()

DOCS_DIR = Path("data/docs")
DB_DIR = "chroma_db"
AUDIT_LOG = Path("logs/audit.jsonl")
MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")  # set LLM_MODEL in .env to change
K = 5

ROLE_ACCESS = {
    "employee": ["public"],
    "hr": ["public", "hr"],
    "finance": ["public", "finance"],
    "engineering": ["public", "engineering"],
    "admin": ["public", "hr", "finance", "engineering"],
}

SYSTEM = (
    "Answer using only the numbered sources provided. "
    "Cite sources as [1], [2] after each claim. "
    "If the sources don't contain the answer, say you don't know."
)
SYSTEM_REDACTED = SYSTEM + (
    " Personal data in the sources and question has been replaced by placeholders such as "
    "<PERSON_1> or <US_SSN_1>. When you refer to such a value, write the placeholder exactly as given."
)

embedder = SentenceTransformer("all-MiniLM-L6-v2")
llm = anthropic.Anthropic()
db = chromadb.PersistentClient(path=DB_DIR)
collection = db.get_or_create_collection("docs")


def chunk_text(text, min_chars=400):
    """Split on blank lines, then merge paragraphs until a chunk is at least min_chars long."""
    chunks, buf = [], ""
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        buf = f"{buf}\n\n{para}" if buf else para
        if len(buf) >= min_chars:
            chunks.append(buf)
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def build_index():
    """Rebuild the vector index from data/docs/*.md."""
    global collection
    try:
        db.delete_collection("docs")
    except Exception:
        pass
    collection = db.create_collection("docs")

    ids, texts, metas = [], [], []
    for path in sorted(DOCS_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip()
        department = path.stem.split("_")[0]  # public / hr / finance / engineering
        for i, chunk in enumerate(chunk_text(text)):
            ids.append(f"{path.name}::{i}")
            texts.append(chunk)
            metas.append(
                {"doc_id": path.name, "title": title, "department": department, "chunk": i}
            )

    if not texts:
        sys.exit(f"No .md files found in {DOCS_DIR}. Add your documents first.")

    embeddings = embedder.encode(texts, normalize_embeddings=True).tolist()
    collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metas)
    print(f"Indexed {len(texts)} chunks from {len({m['doc_id'] for m in metas})} documents.")


def retrieve(question, k=K, user_role=None):
    """Top-k chunks. With a user_role, the search is limited to departments that role may see."""
    where = None
    if user_role is not None:
        if user_role not in ROLE_ACCESS:
            raise ValueError(f"Unknown role: {user_role}")
        where = {"department": {"$in": ROLE_ACCESS[user_role]}}
    q_emb = embedder.encode([question], normalize_embeddings=True).tolist()
    res = collection.query(query_embeddings=q_emb, n_results=k, where=where)
    return res["documents"][0], res["metadatas"][0]


def audit(user_role, question, metas, redacted):
    AUDIT_LOG.parent.mkdir(exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "role": user_role,
        "question": question,  # already redacted when redaction is on, so logs hold no PII
        "retrieved": [m["doc_id"] for m in metas],
        "redacted": redacted,
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def ask(question, k=K, user_role=None, redact=False):
    chunks, metas = retrieve(question, k, user_role)

    redactor = Redactor() if redact else None
    q_text = redactor.redact(question) if redact else question
    c_texts = [redactor.redact(c) for c in chunks] if redact else chunks
    audit(user_role, q_text, metas, redact)

    context = "\n\n".join(
        f"[{i}] ({m['title']})\n{c}" for i, (c, m) in enumerate(zip(c_texts, metas), 1)
    )
    user_content = f"Sources:\n{context}\n\nQuestion: {q_text}"

    msg = llm.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM_REDACTED if redact else SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    answer = msg.content[0].text
    if redact:
        answer = redactor.restore(answer)

    # Validate citations in code: every [n] must map to a real retrieved chunk.
    cited = set()
    for group in re.findall(r"\[([\d,\s]+)\]", answer):
        cited.update(int(n) for n in re.split(r"[,\s]+", group.strip()) if n)
    valid = sorted(n for n in cited if 1 <= n <= len(chunks))
    invalid = sorted(n for n in cited if n not in valid)

    return {
        "answer": answer,
        "sources": [
            {"n": n, "doc_id": metas[n - 1]["doc_id"], "title": metas[n - 1]["title"]}
            for n in valid
        ],
        "invalid_citations": invalid,
        "retrieved_docs": [m["doc_id"] for m in metas],  # used for retrieval hit rate
        "outgoing": user_content,  # exactly what was sent to the LLM, used to test for leaks
    }


def show(result):
    print("\n" + result["answer"])
    print("\nSources:")
    for s in result["sources"]:
        print(f"  [{s['n']}] {s['doc_id']} ({s['title']})")
    if not result["sources"]:
        print("  (none cited)")
    if result["invalid_citations"]:
        print(f"  WARNING: answer cited nonexistent sources {result['invalid_citations']}")


if __name__ == "__main__":
    if "--reindex" in sys.argv or collection.count() == 0:
        build_index()
    role = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--role=")), None)
    redact = "--redact" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        show(ask(" ".join(args), user_role=role, redact=redact))
    else:
        while True:
            q = input("\nQuestion (blank to quit): ").strip()
            if not q:
                break
            show(ask(q, user_role=role, redact=redact))
