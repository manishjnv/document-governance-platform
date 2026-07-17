# Coding Standards

Standards for all contributions to the EDGP project.

## General Principles

1. **Readability first** — Code is read 10x more than it's written
2. **Consistency** — Follow established patterns
3. **Simplicity** — Don't over-engineer
4. **Testability** — Write code that can be tested
5. **Documentation** — Explain the "why" not the "what"

## Python (Backend)

### Style Guide: PEP 8

```bash
# Format code
black apps/api

# Check formatting
flake8 apps/api

# Sort imports
isort apps/api
```

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Package | lowercase | `app`, `models`, `routers` |
| Module | lowercase_underscore | `auth_service.py` |
| Class | PascalCase | `UserRepository` |
| Function | lowercase_underscore | `get_user_by_id()` |
| Constant | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| Private | leading `_` | `_internal_method()` |

### Folder Structure

```
apps/api/
├── main.py              # Entry point
├── app/
│   ├── __init__.py
│   ├── config.py        # Settings
│   ├── dependencies.py  # Shared dependencies
│   ├── models/          # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── document.py
│   │   └── review.py
│   ├── schemas/         # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── document.py
│   ├── routers/         # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── documents.py
│   │   └── reviews.py
│   ├── services/        # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   └── review_service.py
│   ├── ai/              # AI agents & orchestration
│   │   ├── __init__.py
│   │   ├── agents/
│   │   ├── orchestrator.py
│   │   └── prompts.py
│   └── db/              # Database utilities
│       ├── __init__.py
│       ├── session.py
│       └── base.py
├── migrations/          # Alembic migrations
├── tests/               # Unit & integration tests
│   ├── test_auth.py
│   ├── test_documents.py
│   └── fixtures.py
├── requirements.txt
└── .env.example
```

### Type Hints

Always use type hints:

```python
# ✓ Good
def get_user(user_id: int) -> User:
    return db.query(User).filter(User.id == user_id).first()

# ✗ Bad
def get_user(user_id):
    return db.query(User).filter(User.id == user_id).first()
```

### Docstrings

Use Google-style docstrings:

```python
def calculate_score(findings: list[Finding]) -> dict:
    """
    Calculate overall document score from findings.

    Args:
        findings: List of Finding objects from review.

    Returns:
        Dictionary with scores:
        {
            "overall": 0-100,
            "completeness": 0-100,
            "clarity": 0-100,
            ...
        }

    Raises:
        ValueError: If findings list is empty.
    """
    if not findings:
        raise ValueError("Cannot score empty findings list")
    # Implementation...
```

### Error Handling

Always handle errors explicitly:

```python
# ✓ Good
try:
    user = db.query(User).filter(User.id == user_id).first()
except SQLAlchemyError as e:
    logger.error(f"Database error fetching user {user_id}: {e}")
    raise HTTPException(status_code=500, detail="Database error")

# ✗ Bad
try:
    user = db.query(User).filter(User.id == user_id).first()
except:
    pass  # Silent failure
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"Starting review for document {doc_id}")
logger.warning(f"High memory usage: {memory_mb}MB")
logger.error(f"Failed to parse document: {error}", exc_info=True)
```

## TypeScript/JavaScript (Frontend)

### Style Guide: Airbnb + Prettier

```bash
# Format code
npm run format

# Check linting
npm run lint

# Type check
npm run type-check
```

### Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Component | PascalCase | `DocumentUpload.tsx` |
| Hook | camelCase, prefix `use` | `useDocumentUpload.ts` |
| Constant | UPPER_SNAKE_CASE | `MAX_FILE_SIZE` |
| Function | camelCase | `getDocumentById()` |
| Private/Internal | leading `_` | `_handleError()` |
| CSS classes | kebab-case | `document-upload` |

### Folder Structure

```
apps/web/src/
├── app/                 # Next.js app directory
│   ├── layout.tsx
│   ├── page.tsx
│   ├── (auth)/
│   │   ├── login/
│   │   └── register/
│   └── (dashboard)/
│       ├── documents/
│       ├── reviews/
│       └── dashboard/
├── components/          # Reusable components
│   ├── ui/              # UI primitives (shadcn/ui)
│   │   ├── Button.tsx
│   │   ├── Modal.tsx
│   │   └── Card.tsx
│   ├── layout/          # Layout components
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── Footer.tsx
│   └── forms/           # Form components
│       ├── DocumentUploadForm.tsx
│       └── ReviewFilterForm.tsx
├── hooks/               # Custom React hooks
│   ├── useAuth.ts
│   ├── useDocuments.ts
│   └── useReview.ts
├── api/                 # API client functions
│   ├── client.ts
│   ├── auth.ts
│   ├── documents.ts
│   └── reviews.ts
├── types/               # TypeScript types
│   ├── index.ts
│   ├── auth.ts
│   ├── document.ts
│   └── review.ts
├── utils/               # Utility functions
│   ├── format.ts
│   ├── validate.ts
│   └── helpers.ts
├── styles/              # Global styles
│   └── globals.css
└── constants/           # Constants
    └── config.ts
```

### Component Pattern

```typescript
// ✓ Good component structure
import React from 'react'
import { DocumentUploadProps } from '@/types'
import { Button } from '@/components/ui/Button'

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onSuccess,
  maxSize = 50,
}) => {
  const [isLoading, setIsLoading] = React.useState(false)

  const handleUpload = async (file: File) => {
    setIsLoading(true)
    try {
      await uploadDocument(file)
      onSuccess?.()
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <input type="file" onChange={(e) => handleUpload(e.target.files?.[0]!)} />
      <Button disabled={isLoading}>
        {isLoading ? 'Uploading...' : 'Upload'}
      </Button>
    </div>
  )
}
```

### Type Definitions

```typescript
// ✓ Always export types
export interface Document {
  id: string
  filename: string
  uploadedAt: Date
  status: 'pending' | 'processing' | 'completed' | 'error'
}

export interface ReviewFinding {
  id: string
  documentId: string
  severity: 'critical' | 'major' | 'medium' | 'low' | 'info'
  category: string
  description: string
  evidence: string
  recommendation: string
  confidence: number
}
```

## Commit Message Format

```
T-XXX: Brief description (50 chars max)

Longer explanation if needed (72 chars per line).
Describe the "why" not the "what".

Closes #123
```

### Examples

```
T-001: Create monorepo structure

Sets up initial project structure with apps/, packages/, and docs/
directories for frontend, backend, and shared code organization.

T-102: Implement JWT token validation

Adds middleware to validate JWT tokens on protected endpoints.
Tokens checked in Authorization header with Bearer scheme.
Returns 401 for invalid/expired tokens.
```

## Pull Request Checklist

Before submitting:

- [ ] Code follows style guide (ran linters)
- [ ] Type checking passes (Python: mypy, TypeScript: tsc)
- [ ] Tests written and passing
- [ ] Docstrings/comments added for complex logic
- [ ] No debug console.logs or print statements left
- [ ] Environment variables documented in .env.example
- [ ] Commit messages follow format
- [ ] Squash related commits

## Testing

### Python (pytest)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test
pytest tests/test_auth.py::test_login_success
```

### TypeScript (Jest, Vitest)

```bash
# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run in watch mode
npm test -- --watch
```

### Test Naming

```python
# Python
def test_get_user_by_id_returns_user():
    # Arrange
    user_id = 1
    
    # Act
    user = get_user_by_id(user_id)
    
    # Assert
    assert user is not None
    assert user.id == user_id
```

```typescript
// TypeScript
describe('getDocumentById', () => {
  it('should return document when found', async () => {
    // Arrange
    const docId = 'doc-123'

    // Act
    const doc = await getDocumentById(docId)

    // Assert
    expect(doc).toBeDefined()
    expect(doc.id).toBe(docId)
  })
})
```

## Security Guidelines

1. **Never commit secrets** — Use `.env` files
2. **Validate inputs** — On all API endpoints
3. **Sanitize outputs** — Especially user data
4. **Use HTTPS** — Always in production
5. **Authenticate requests** — JWT tokens for API
6. **Log security events** — Failed auth attempts, etc.

## Performance Guidelines

1. **Cache wisely** — Use Redis for frequently accessed data
2. **Paginate results** — Never return unlimited lists
3. **Index databases** — On foreign keys and filters
4. **Lazy load components** — Use React.lazy() for large components
5. **Profile before optimizing** — Use tools to measure

## Documentation Guidelines

1. **README in each folder** — Explain purpose
2. **Comment complex logic** — But not obvious code
3. **Update docs with code** — Don't let docs rot
4. **Include examples** — Show how to use
5. **Document assumptions** — Edge cases, constraints

## Review Process

Reviewers check:

- [ ] Code follows standards
- [ ] Logic is correct
- [ ] Tests cover changes
- [ ] Performance is acceptable
- [ ] Security concerns addressed
- [ ] Documentation updated

---

**Questions?** Ask in team Slack or open an issue.
