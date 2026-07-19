"""Project endpoints (Phase A of Document Lifecycle plan): list with
per-project rollup stats, and create."""

import logging
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
    existing = await db.execute(
        select(Project).where(and_(Project.org_id == org_id, Project.name == name))
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project '{name}' already exists in this organization",
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
    one-round-trip flow), or reuses the existing one on a name collision."""
    name = name.strip()
    existing = await db.execute(
        select(Project).where(and_(Project.org_id == org_id, Project.name == name))
    )
    project = existing.scalar_one_or_none()
    if project is not None:
        return project

    project = Project(org_id=org_id, name=name)
    db.add(project)
    await db.flush()
    return project
