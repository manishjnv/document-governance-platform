"""Project endpoints (Phase A of Document Lifecycle plan): list with
per-project rollup stats, and create."""

import difflib
import logging
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, verify_org_access
from app.models.document import Document
from app.models.finding import Finding
from app.models.project import Project
from app.models.review import Review
from app.schemas.auth import TokenData
from app.schemas.project import ProjectCreate, ProjectRead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

# A typed project name is considered "the same project" as an existing one
# when either: the names are equal ignoring case (capitalization alone
# never creates a new project), or they're >=90% similar after stripping
# generic company-type/descriptor words (typo/whitespace/punctuation drift,
# and "Acme Corporation" vs "Acme Ltd" vs "Acme" all being the same
# customer). Matches the fuzzy-match approach already used for filename
# similarity in app/insights/similarity.py.
PROJECT_NAME_MATCH_THRESHOLD = 0.9

# Legal-entity suffixes and generic business descriptors -- not part of a
# company's distinctive identity, so ignored when deciding whether two
# project names refer to the same underlying project/customer.
_COMPANY_SUFFIX_RE = re.compile(
    r"\b("
    r"corp|corporation|inc|incorporated|llc|ltd|limited|llp|plc|co|company|"
    r"technologies|technology|tech|solutions|systems|services|software|"
    r"labs|laboratories|group|holdings|enterprises|industries|"
    r"international|global"
    r")\.?\b",
    re.IGNORECASE,
)


def _normalize_project_name(name: str) -> str:
    """Lowercased, company-suffix-stripped, whitespace-collapsed name used
    for both the exact and fuzzy match comparisons below. Falls back to the
    plain lowercased name if stripping suffixes would eat the whole name
    (e.g. a project literally named "Technologies") -- an empty normalized
    string would otherwise make every such name match every other one."""
    lowered = name.lower()
    stripped = re.sub(r"\s+", " ", _COMPANY_SUFFIX_RE.sub("", lowered)).strip()
    return stripped or lowered.strip()


async def find_matching_project(db: AsyncSession, org_id: UUID, name: str) -> Project | None:
    """Case-insensitive exact match first, then >=90% fuzzy match against
    every existing project name in the org -- both comparisons run on
    company-suffix-normalized names. Returns the best match or None."""
    result = await db.execute(select(Project).where(Project.org_id == org_id))
    candidates = result.scalars().all()

    normalized_name = _normalize_project_name(name)
    for candidate in candidates:
        if _normalize_project_name(candidate.name) == normalized_name:
            return candidate

    best_match, best_score = None, 0.0
    for candidate in candidates:
        score = difflib.SequenceMatcher(
            None, normalized_name, _normalize_project_name(candidate.name)
        ).ratio()
        if score > best_score:
            best_match, best_score = candidate, score

    if best_match is not None and best_score >= PROJECT_NAME_MATCH_THRESHOLD:
        return best_match

    return None


@router.get("", response_model=list[ProjectRead], summary="List organization projects")
async def list_projects(
    org_id: UUID = Query(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(str(org_id), current_user)

    result = await db.execute(
        select(Project).where(Project.org_id == org_id).order_by(Project.name)
    )
    projects = result.scalars().all()

    reads = []
    for project in projects:
        doc_result = await db.execute(
            select(Document.doc_id).where(
                and_(Document.project_id == project.project_id, Document.deleted_at.is_(None))
            )
        )
        doc_ids = [row[0] for row in doc_result.all()]

        average_latest_score = None
        open_critical_count = 0
        if doc_ids:
            # Latest completed review per document, one query.
            review_result = await db.execute(
                select(Review)
                .where(Review.doc_id.in_(doc_ids) & (Review.deleted_at.is_(None)))
                .order_by(Review.doc_id, Review.created_at.desc())
            )
            latest_review_by_doc: dict = {}
            for review in review_result.scalars().all():
                latest_review_by_doc.setdefault(review.doc_id, review)

            completed_scores = [
                float(r.overall_score)
                for r in latest_review_by_doc.values()
                if r.status == "completed" and r.overall_score is not None
            ]
            if completed_scores:
                average_latest_score = sum(completed_scores) / len(completed_scores)

            review_ids = [r.review_id for r in latest_review_by_doc.values()]
            if review_ids:
                critical_result = await db.execute(
                    select(func.count(func.distinct(Finding.review_id))).where(
                        and_(
                            Finding.review_id.in_(review_ids),
                            Finding.severity == "critical",
                            Finding.status == "open",
                            Finding.deleted_at.is_(None),
                        )
                    )
                )
                open_critical_count = critical_result.scalar() or 0

        reads.append(
            ProjectRead(
                project_id=project.project_id,
                org_id=project.org_id,
                name=project.name,
                created_at=project.created_at,
                document_count=len(doc_ids),
                average_latest_score=average_latest_score,
                open_critical_count=open_critical_count,
            )
        )

    return reads


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
async def create_project(
    payload: ProjectCreate,
    org_id: UUID = Query(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await verify_org_access(str(org_id), current_user)

    name = payload.name.strip()
    existing = await find_matching_project(db, org_id, name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A matching project already exists in this organization: '{existing.name}'",
        )

    project = Project(org_id=org_id, name=name)
    db.add(project)
    await db.commit()
    await db.refresh(project)

    return ProjectRead(
        project_id=project.project_id,
        org_id=project.org_id,
        name=project.name,
        created_at=project.created_at,
        document_count=0,
        average_latest_score=None,
        open_critical_count=0,
    )


async def get_or_create_project(
    db: AsyncSession, org_id: UUID, name: str
) -> Project:
    """Used by the upload endpoint's project_name fallback -- creates the
    Project row on the fly if it doesn't exist yet (keeps 'create new' a
    one-round-trip flow), or reuses an existing project that matches by
    case-insensitive/fuzzy name (find_matching_project) so a typo or a
    different capitalization doesn't silently fork a new project."""
    name = name.strip()
    existing = await find_matching_project(db, org_id, name)
    if existing is not None:
        return existing

    project = Project(org_id=org_id, name=name)
    db.add(project)
    await db.flush()
    return project
