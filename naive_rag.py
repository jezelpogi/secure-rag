"""Naive RAG baseline: no access control, no PII redaction. Used to measure the starting point."""
import os
import re
import sys
from pathlib import Path

import anthropic
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

DOCS_DIR = Path("data/docs")
DB_DIR = "chroma_db"
MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")  # set LLM_MODEL in .env to change
K = 5

SYSTEM = (
    "Answer using only the numbered sources provided. "
    "Cite sources as [1], [2] after each claim. "
    "If the sources don't contain the answer, say you don't know."
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


def ask(question, k=K):
    q_emb = embedder.encode([question], normalize_embeddings=True).tolist()
    res = collection.query(query_embeddings=q_emb, n_results=k)
    chunks, metas = res["documents"][0], res["metadatas"][0]

    context = "\n\n".join(
        f"[{i}] ({m['title']})\n{c}" for i, (c, m) in enumerate(zip(chunks, metas), 1)
    )
    msg = llm.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM,
        messages=[{"role": "user", "content": f"Sources:\n{context}\n\nQuestion: {question}"}],
    )
    answer = msg.content[0].text

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
        "retrieved_docs": [m["doc_id"] for m in metas],  # used later for retrieval hit rate
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
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if args:
        show(ask(" ".join(args)))
    else:
        while True:
            q = input("\nQuestion (blank to quit): ").strip()
            if not q:
                break
            show(ask(q))
