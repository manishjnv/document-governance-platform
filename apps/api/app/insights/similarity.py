# ponytail: TF cosine similarity, not real semantic embeddings; upgrade to an
# embeddings provider (OpenAI/Anthropic/local) once one is actually configured
# in this repo.
"""Term-frequency cosine similarity + duplicate/similar-document lookups.

T-2026 (similarity), T-2027 (duplicates). No new schema: reads existing
Document rows (parsed_text) org-scoped, deleted_at IS NULL.
"""

import math
import uuid
from collections import Counter

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


def compute_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between whitespace-tokenized, lowercased term-frequency
    vectors. Returns 0.0 for empty/whitespace-only input (no shared terms)."""
    if not text_a or not text_b:
        return 0.0

    tokens_a = text_a.lower().split()
    tokens_b = text_b.lower().split()
    if not tokens_a or not tokens_b:
        return 0.0

    vec_a = Counter(tokens_a)
    vec_b = Counter(tokens_b)

    shared_terms = vec_a.keys() & vec_b.keys()
    dot = sum(vec_a[t] * vec_b[t] for t in shared_terms)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

    return dot / (mag_a * mag_b)


async def _org_documents(db: AsyncSession, org_id: uuid.UUID) -> list[Document]:
    result = await db.execute(
        select(Document).where(
            and_(Document.org_id == org_id, Document.deleted_at.is_(None))
        )
    )
    return list(result.scalars().all())


async def find_similar_documents(
    db: AsyncSession,
    org_id: uuid.UUID,
    doc_id: uuid.UUID,
    threshold: float = 0.5,
    limit: int = 10,
) -> list[dict]:
    """T-2026: documents in the org whose parsed_text is similar to doc_id's,
    above threshold, sorted by score desc.

    # ponytail: O(n) scan comparing against every other doc in the org on
    # every call — fine at this repo's current scale. If org doc counts grow
    # large, revisit with a precomputed similarity index / embeddings store
    # rather than building one speculatively now.
    """
    target_result = await db.execute(
        select(Document).where(
            and_(
                Document.doc_id == doc_id,
                Document.org_id == org_id,
                Document.deleted_at.is_(None),
            )
        )
    )
    target = target_result.scalar_one_or_none()
    if target is None or not target.parsed_text:
        return []

    scored = []
    for doc in await _org_documents(db, org_id):
        if doc.doc_id == doc_id or not doc.parsed_text:
            continue
        score = compute_similarity(target.parsed_text, doc.parsed_text)
        if score >= threshold:
            scored.append(
                {"doc_id": str(doc.doc_id), "filename": doc.filename, "similarity": score}
            )

    scored.sort(key=lambda d: d["similarity"], reverse=True)
    return scored[:limit]


async def find_duplicates(
    db: AsyncSession, org_id: uuid.UUID, threshold: float = 0.9
) -> list[dict]:
    """T-2027: pairs of documents in the org whose parsed_text similarity is
    at/above threshold. Each unordered pair appears once.

    # ponytail: O(n^2) pairwise scan — fine at current scale, revisit if org
    # doc counts grow large.
    """
    docs = [d for d in await _org_documents(db, org_id) if d.parsed_text]

    pairs = []
    for i in range(len(docs)):
        for j in range(i + 1, len(docs)):
            score = compute_similarity(docs[i].parsed_text, docs[j].parsed_text)
            if score >= threshold:
                pairs.append(
                    {
                        "doc_id_a": str(docs[i].doc_id),
                        "doc_id_b": str(docs[j].doc_id),
                        "similarity": score,
                    }
                )

    pairs.sort(key=lambda p: p["similarity"], reverse=True)
    return pairs
