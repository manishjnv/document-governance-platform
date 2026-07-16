# Authentication API Documentation

**T-113: Auth API Specification**

Base URL: `http://localhost:8000/api/v1/auth`

All requests/responses are JSON. Authentication uses Bearer tokens in the `Authorization` header.

---

## Endpoints

### 1. Login

**POST** `/login`

Authenticate with email and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400,
  "token_type": "bearer",
  "user_id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "org_id": 1,
  "role": "admin"
}
```

**Errors:**
- `401 Unauthorized`: Invalid email or password
- `429 Too Many Requests`: Too many failed login attempts

---

### 2. Refresh Token

**POST** `/refresh`

Get a new access token using a refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 86400,
  "token_type": "bearer"
}
```

**Errors:**
- `401 Unauthorized`: Invalid or expired refresh token

---

### 3. Get Current User

**GET** `/me`

Get current authenticated user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "user_id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "org_id": 1,
  "org_name": "Acme Corp",
  "role": "admin",
  "mfa_enabled": false,
  "created_at": "2026-07-01T10:00:00Z",
  "last_login": "2026-07-17T14:30:00Z"
}
```

**Errors:**
- `401 Unauthorized`: Missing or invalid token

---

### 4. Logout

**POST** `/logout`

Logout current user (invalidate tokens).

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response (200 OK):**
```json
{
  "message": "Successfully logged out"
}
```

**Errors:**
- `401 Unauthorized`: Missing or invalid token

**Note:** In JWT auth, tokens remain valid until expiration. For true logout:
- Use token blacklist (Redis)
- Implement short token expiration times
- Consider refresh token rotation

---

### 5. Request Password Reset

**POST** `/password-reset`

Request a password reset email.

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "message": "If email exists, password reset link sent"
}
```

**Security Note:** Always returns 200 to avoid email enumeration attacks.

---

### 6. Confirm Password Reset

**POST** `/password-reset/confirm`

Confirm password reset with new password.

**Request:**
```json
{
  "token": "reset-token-from-email",
  "new_password": "newpassword456"
}
```

**Response (200 OK):**
```json
{
  "message": "Password successfully reset"
}
```

**Errors:**
- `400 Bad Request`: Invalid or expired token
- `404 Not Found`: User not found

---

### 7. Change Password

**POST** `/change-password`

Change password for authenticated user.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "current_password": "oldpassword",
  "new_password": "newpassword456"
}
```

**Response (200 OK):**
```json
{
  "message": "Password successfully changed"
}
```

**Errors:**
- `401 Unauthorized`: Missing token or incorrect current password
- `404 Not Found`: User not found

---

## Authentication

All protected endpoints require the `Authorization` header with a Bearer token:

```
Authorization: Bearer <access_token>
```

**Token Format:** JWT with three parts separated by dots
- Header: Algorithm and token type
- Payload: User info and expiration
- Signature: Cryptographic signature

**Token Expiration:**
- Access token: 24 hours (configurable in .env)
- Refresh token: 7 days (configurable in .env)

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common Status Codes:**
- `400 Bad Request`: Invalid input or validation error
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Authenticated but not authorized
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error (invalid data type/format)
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

## Rate Limiting

**Phase 1:** Simple in-memory rate limiter (5 failed login attempts per 15 minutes)

**Future:** Redis-based distributed rate limiting with:
- Per-IP rate limits
- Per-user rate limits
- Configurable thresholds

---

## Examples

### Login Flow

```bash
# 1. Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123"
  }'

# Response includes access_token and refresh_token

# 2. Use access token to access protected endpoints
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# 3. When access token expires, use refresh token
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<refresh_token>"
  }'
```

### Password Reset Flow

```bash
# 1. Request password reset
curl -X POST http://localhost:8000/api/v1/auth/password-reset \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'

# 2. User receives email with reset link containing token
# 3. User clicks link and enters new password
curl -X POST http://localhost:8000/api/v1/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "token": "reset-token-from-email",
    "new_password": "newpassword456"
  }'
```

---

## Future Enhancements

- [ ] Azure AD / Entra ID OAuth integration (T-109)
- [ ] Multi-factor authentication (MFA)
- [ ] Social login (Google, GitHub)
- [ ] Token blacklist for true logout
- [ ] Session management dashboard
- [ ] Login history and device tracking
- [ ] IP-based access restrictions
- [ ] API key authentication for service-to-service
