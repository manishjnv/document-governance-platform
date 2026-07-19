# ponytail: TF cosine similarity, not real semantic embeddings; upgrade to an
# embeddings provider (OpenAI/Anthropic/local) once one is actually configured
# in this repo.
"""Term-frequency cosine similarity + duplicate/similar-document lookups.

T-2026 (similarity), T-2027 (duplicates). No new schema: reads existing
Document rows (parsed_text) org-scoped, deleted_at IS NULL.
"""

import math
import re
import uuid
from collections import Counter
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_link_suggestion import DocumentLinkSuggestion
from app.models.organization import Organization

# Strips common version-marker noise ("_v2", " (revised)", "-v3", "(final)",
# "copy") so two uploads of the same underlying document compare as similar
# filenames even when their version suffix differs.
_VERSION_SUFFIX_RE = re.compile(
    r"[\s_\-]*\(?(v\d+|version\s*\d+|revised|final|copy|draft)\)?", re.IGNORECASE
)


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


def _normalized_filename(filename: str) -> str:
    """Lowercased filename stem with version-suffix noise stripped, for
    fuzzy version-match comparison (T-2028 versioning suggestion, Phase B)."""
    stem = filename.rsplit(".", 1)[0]
    stem = _VERSION_SUFFIX_RE.sub("", stem)
    return re.sub(r"[^a-z0-9]+", "", stem.lower())


def filename_similarity(name_a: str, name_b: str) -> float:
    """difflib ratio between version-suffix-stripped, normalized filenames."""
    import difflib

    norm_a, norm_b = _normalized_filename(name_a), _normalized_filename(name_b)
    if not norm_a or not norm_b:
        return 0.0
    return difflib.SequenceMatcher(None, norm_a, norm_b).ratio()


async def suggest_version_link(
    db: AsyncSession, org_id: uuid.UUID, doc: Document
) -> DocumentLinkSuggestion | None:
    """T-2028/2029 support (Phase B, Document Lifecycle plan): after any
    upload, check whether `doc` looks like a new version of an existing,
    *different* document group -- same org, meaningful parsed_text overlap
    or version-suffix-insensitive filename match. Never auto-links; only
    stores a dismissible suggestion pointing at the best-matching group's
    latest version. Idempotent per doc_id (unique constraint on doc_id).

    # ponytail: whichever of text/filename similarity scores higher wins --
    # a simple max, not a weighted blend. Good enough for a first-pass
    # heuristic; revisit if false-positive/negative rate in practice
    # warrants a real blended score.
    """
    org_result = await db.execute(select(Organization).where(Organization.org_id == org_id))
    org = org_result.scalar_one_or_none()
    threshold = float(org.similarity_suggestion_threshold) if org else 0.55

    candidates = [
        d
        for d in await _org_documents(db, org_id)
        if d.doc_id != doc.doc_id and d.document_group_id != doc.document_group_id
    ]
    if not candidates:
        return None

    best_doc = None
    best_score = 0.0
    for candidate in candidates:
        text_score = (
            compute_similarity(doc.parsed_text, candidate.parsed_text)
            if doc.parsed_text and candidate.parsed_text
            else 0.0
        )
        name_score = filename_similarity(
            doc.original_filename or doc.filename, candidate.original_filename or candidate.filename
        )
        score = max(text_score, name_score)
        if score > best_score:
            best_score, best_doc = score, candidate

    if best_doc is None or best_score < threshold:
        return None

    # Point the suggestion at the latest version within the matched group.
    group_result = await db.execute(
        select(Document)
        .where(
            and_(
                Document.document_group_id == best_doc.document_group_id,
                Document.org_id == org_id,
                Document.deleted_at.is_(None),
            )
        )
        .order_by(Document.version.desc())
    )
    latest_in_group = group_result.scalars().first()

    suggestion = DocumentLinkSuggestion(
        org_id=org_id,
        doc_id=doc.doc_id,
        suggested_doc_id=latest_in_group.doc_id,
        similarity_score=Decimal(str(round(best_score, 4))),
        status="pending",
    )
    db.add(suggestion)
    await db.flush()
    return suggestion


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
