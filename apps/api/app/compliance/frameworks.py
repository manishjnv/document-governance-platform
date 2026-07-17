"""Compliance framework control management.

T-2051 (SOC2), T-2052 (ISO27001), T-2053 (GDPR), T-2054 (HIPAA),
T-2055 (compliance report generation)

DISCLAIMER: This module provides a self-reported implementation status
tracker for starter compliance-control checklists. It is NOT a certification,
audit, or legal guarantee of compliance. Use it for internal tracking only.
"""

import csv
import io
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance_control import ComplianceControl

logger = logging.getLogger(__name__)

# Starter checklists per framework (control_code, description pairs)
# These are representative common-criteria items, not exhaustive/authoritative
DEFAULT_CONTROLS: dict[str, list[tuple[str, str]]] = {
    "SOC2": [
        ("CC6.1", "Access control policies and procedures are defined and documented"),
        ("CC6.2", "User access provisioning and de-provisioning processes are implemented"),
        ("CC7.1", "Change management procedures are established and followed"),
        ("CC7.2", "Emergency change procedures are defined and tested"),
        ("A1.1", "System monitoring and logging are implemented"),
        ("A1.2", "Incident response procedures are documented"),
        ("D1.1", "Data encryption in transit is enforced"),
        ("D1.2", "Data encryption at rest is enforced"),
    ],
    "ISO27001": [
        ("A.5.1", "Information security policies are established and communicated"),
        ("A.6.1", "Organization of information security responsibilities"),
        ("A.7.1", "Human resource security – prior to employment"),
        ("A.8.1", "Asset management – inventory and classification"),
        ("A.9.1", "Access control – user registration and de-registration"),
        ("A.10.1", "Cryptography controls are in place"),
        ("A.12.4", "Logging and monitoring of user activities"),
        ("A.16.1", "Incident management procedures are established"),
    ],
    "GDPR": [
        ("DPA", "Data Processing Agreement in place with processors"),
        ("LB", "Lawful basis for processing documented"),
        ("DR", "Data subject rights procedures implemented"),
        ("BR", "Breach notification procedures established"),
        ("DPO", "Data Protection Officer appointed (if required)"),
        ("DPIA", "Data Protection Impact Assessments performed"),
        ("CON", "Data retention/deletion procedures in place"),
        ("EC", "Export control and cross-border transfer rules followed"),
    ],
    "HIPAA": [
        ("AC", "Access controls and authentication mechanisms implemented"),
        ("AU", "Audit controls and logging in place"),
        ("AR", "Integrity controls to protect health information"),
        ("TR", "Transmission security for electronic protected health information"),
        ("PE", "Physical access controls and safeguards"),
        ("BAA", "Business Associate Agreements executed with vendors"),
        ("BR", "Breach notification procedures and incident response"),
        ("REC", "Disaster recovery and business continuity planning"),
    ],
}


async def seed_framework_controls(
    db: AsyncSession, org_id: UUID, framework: str
) -> int:
    """
    Seed starter control checklist for a framework in an organization.

    Idempotent: checks for existing (org_id, framework) rows first.

    Args:
        db: Database session
        org_id: Organization ID
        framework: Framework name ('SOC2', 'ISO27001', 'GDPR', 'HIPAA')

    Returns:
        Count of controls inserted
    """
    if framework not in DEFAULT_CONTROLS:
        logger.warning(f"Unknown framework: {framework}")
        return 0

    # Check if controls already exist for this org/framework
    query = select(ComplianceControl).where(
        and_(
            ComplianceControl.org_id == org_id,
            ComplianceControl.framework == framework,
        )
    )
    existing = await db.execute(query)
    if existing.scalars().first():
        logger.info(f"Controls already seeded for org {org_id}, framework {framework}")
        return 0

    # Seed default controls
    controls = [
        ComplianceControl(
            org_id=org_id,
            framework=framework,
            control_code=code,
            description=desc,
            status="not_started",
        )
        for code, desc in DEFAULT_CONTROLS[framework]
    ]

    db.add_all(controls)
    await db.flush()

    logger.info(f"Seeded {len(controls)} controls for org {org_id}, framework {framework}")
    return len(controls)


async def get_framework_status(
    db: AsyncSession, org_id: UUID, framework: str
) -> dict:
    """
    Get implementation status summary for a framework.

    Args:
        db: Database session
        org_id: Organization ID
        framework: Framework name

    Returns:
        Dict with framework, total_controls, by_status counts, and percent_implemented
    """
    query = select(ComplianceControl).where(
        and_(
            ComplianceControl.org_id == org_id,
            ComplianceControl.framework == framework,
        )
    )
    result = await db.execute(query)
    controls = result.scalars().all()

    by_status = {
        "not_started": sum(1 for c in controls if c.status == "not_started"),
        "in_progress": sum(1 for c in controls if c.status == "in_progress"),
        "implemented": sum(1 for c in controls if c.status == "implemented"),
        "verified": sum(1 for c in controls if c.status == "verified"),
    }

    total = len(controls)
    implemented_count = by_status["implemented"] + by_status["verified"]
    percent_implemented = (implemented_count / total * 100) if total > 0 else 0.0

    return {
        "framework": framework,
        "total_controls": total,
        "by_status": by_status,
        "percent_implemented": round(percent_implemented, 1),
    }


async def list_controls(
    db: AsyncSession, org_id: UUID, framework: str
) -> list[dict]:
    """
    List all controls for a framework in an organization.

    Args:
        db: Database session
        org_id: Organization ID
        framework: Framework name

    Returns:
        List of control dicts with control_id, control_code, description, status,
        evidence_notes, last_reviewed_at
    """
    query = (
        select(ComplianceControl)
        .where(
            and_(
                ComplianceControl.org_id == org_id,
                ComplianceControl.framework == framework,
            )
        )
        .order_by(ComplianceControl.control_code)
    )
    result = await db.execute(query)
    controls = result.scalars().all()

    return [
        {
            "control_id": str(c.control_id),
            "control_code": c.control_code,
            "description": c.description,
            "status": c.status,
            "evidence_notes": c.evidence_notes,
            "last_reviewed_at": c.last_reviewed_at.isoformat()
            if c.last_reviewed_at
            else None,
        }
        for c in controls
    ]


async def update_control_status(
    db: AsyncSession,
    org_id: UUID,
    control_id: UUID,
    status: str,
    evidence_notes: Optional[str] = None,
) -> None:
    """
    Update control status and optional evidence notes.

    Sets last_reviewed_at to now() when status changes.

    Args:
        db: Database session
        org_id: Organization ID (for org-scoped query)
        control_id: Control ID to update
        status: New status ('not_started', 'in_progress', 'implemented', 'verified')
        evidence_notes: Optional evidence/implementation notes

    Raises:
        ValueError: If control not found or org mismatch
    """
    # Verify control exists and belongs to org
    query = select(ComplianceControl).where(
        and_(
            ComplianceControl.control_id == control_id,
            ComplianceControl.org_id == org_id,
        )
    )
    result = await db.execute(query)
    control = result.scalars().first()

    if not control:
        raise ValueError(f"Control {control_id} not found in org {org_id}")

    # Update with last_reviewed_at = now()
    stmt = (
        update(ComplianceControl)
        .where(ComplianceControl.control_id == control_id)
        .values(
            status=status,
            evidence_notes=evidence_notes,
            last_reviewed_at=datetime.now(),
        )
    )
    await db.execute(stmt)
    await db.flush()


async def generate_compliance_report(
    db: AsyncSession, org_id: UUID, framework: str
) -> str:
    """
    Generate CSV report of controls and their implementation status.

    Includes a disclaimer line at the top stating this is a self-assessment
    starter checklist, not a certification.

    Args:
        db: Database session
        org_id: Organization ID
        framework: Framework name

    Returns:
        CSV string with columns: control_code, description, status, evidence_notes,
        last_reviewed_at
    """
    query = (
        select(ComplianceControl)
        .where(
            and_(
                ComplianceControl.org_id == org_id,
                ComplianceControl.framework == framework,
            )
        )
        .order_by(ComplianceControl.control_code)
    )
    result = await db.execute(query)
    controls = result.scalars().all()

    output = io.StringIO()

    # Write disclaimer header
    output.write("DISCLAIMER: This is a self-reported starter compliance checklist.")
    output.write(" It is NOT a certification, audit, or legal guarantee of compliance.\n")

    writer = csv.DictWriter(
        output,
        fieldnames=[
            "control_code",
            "description",
            "status",
            "evidence_notes",
            "last_reviewed_at",
        ],
    )

    writer.writeheader()

    for control in controls:
        writer.writerow(
            {
                "control_code": control.control_code,
                "description": control.description,
                "status": control.status,
                "evidence_notes": control.evidence_notes or "",
                "last_reviewed_at": (
                    control.last_reviewed_at.isoformat()
                    if control.last_reviewed_at
                    else ""
                ),
            }
        )

    return output.getvalue()
