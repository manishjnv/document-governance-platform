"""Shared enum vocabularies for EDGP tables.

Single source of truth for every "magic string" column so the allowed
values live in exactly one place and stay in sync with the CHECK
constraints in migrations/001_init_schema.sql. Both the SQLAlchemy models
and the Pydantic schemas import from here.
"""

from enum import Enum


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UserRole(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class FileType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"


class DocumentType(str, Enum):
    SOW = "SOW"
    PROPOSAL = "Proposal"
    OTHER = "Other"


class StorageStatus(str, Enum):
    UPLOADED = "uploaded"
    ARCHIVED = "archived"
    DELETED_FROM_S3 = "deleted_from_s3"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class FindingSource(str, Enum):
    AGENT = "agent"
    RULE = "rule"


class Severity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class BusinessImpact(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class AuditResourceType(str, Enum):
    DOCUMENT = "document"
    REVIEW = "review"
    FINDING = "finding"
    USER = "user"
    ORGANIZATION = "organization"
