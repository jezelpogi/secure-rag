"""The RAG pipeline: retrieve (role-filtered) -> redact PII -> generate -> validate citations.

Command line (from the project root):
    python pipeline.py "your question" --role=hr --redact
    python pipeline.py --role=finance --redact        # interactive
    python pipeline.py --reindex                      # rebuild the index first
"""
import sys

from generation.citations import validate_citations
from generation.prompts import SYSTEM, SYSTEM_REDACTED, build_user_content
from ingest.indexer import build_index
from resources import get_collection, llm
from retrieval.search import retrieve
from security.audit import audit
from security.pii import Redactor
from settings import K, MODEL


def ask(question, k=K, user_role=None, redact=False):
    chunks, metas = retrieve(question, k, user_role)

    redactor = Redactor() if redact else None
    q_text = redactor.redact(question) if redact else question
    c_texts = [redactor.redact(c) for c in chunks] if redact else chunks
    audit(user_role, q_text, metas, redact)

    user_content = build_user_content(q_text, c_texts, metas)
    msg = llm.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM_REDACTED if redact else SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )
    answer = msg.content[0].text
    if redact:
        answer = redactor.restore(answer)

    valid, invalid = validate_citations(answer, len(chunks))
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


def main(argv):
    if "--reindex" in argv or get_collection().count() == 0:
        build_index()
    role = next((a.split("=", 1)[1] for a in argv if a.startswith("--role=")), None)
    redact = "--redact" in argv
    words = [a for a in argv if not a.startswith("--")]
    if words:
        show(ask(" ".join(words), user_role=role, redact=redact))
        return
    while True:
        q = input("\nQuestion (blank to quit): ").strip()
        if not q:
            break
        show(ask(q, user_role=role, redact=redact))


if __name__ == "__main__":
    main(sys.argv[1:])
