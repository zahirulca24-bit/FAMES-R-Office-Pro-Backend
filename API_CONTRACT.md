# Batch 1 API Contract

Base prefix: `/api/v1`

Batch 1 preserves the current frontend authentication contract. No Client or Job contract was added.

## Authentication

### POST `/api/v1/auth/login`

Request JSON:

```json
{
  "login_id": "Admin@001",
  "password": "<user-supplied-password>",
  "remember_me": true
}
```

Success `200` response shape:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "expires_in": 2592000,
  "user": {
    "id": "<uuid>",
    "login_id": "Admin@001",
    "email": "admin@example.com",
    "full_name": "FAMES & R Super Admin",
    "role": "SUPER_ADMIN",
    "status": "ACTIVE",
    "must_change_password": false
  }
}
```

Relevant errors:

- `401` invalid login ID or password
- `403` inactive account
- `423` temporary lock
- `422` request validation failure

### GET `/api/v1/auth/me`

Header: `Authorization: Bearer <access_token>`

Success `200`: the same user object shape shown above.

Relevant errors:

- `401` missing, invalid, expired, revoked, or inactive session

### POST `/api/v1/auth/change-password`

Header: `Authorization: Bearer <access_token>`

Request JSON:

```json
{
  "current_password": "<current-password>",
  "new_password": "<new-password-minimum-10-characters>"
}
```

Success `200`:

```json
{
  "message": "Password changed successfully",
  "reauthentication_required": true
}
```

The password change revokes all existing access tokens for the user.

## Baseline Admin APIs

These are existing foundational APIs, not Batch 2 completion. Both require an active `SUPER_ADMIN` and a completed forced password change.

### POST `/api/v1/admin/users`

Creates one user with a supported baseline role.

Supported baseline roles:

- `SUPER_ADMIN`
- `PARTNER`
- `MANAGER`
- `ASSISTANT_DEVELOPER`
- `STUDENT`

Relevant errors: `401`, `403`, `409`, `422`.

### PATCH `/api/v1/admin/users/{login_id}/status`

Request JSON:

```json
{
  "status": "SUSPENDED"
}
```

Allowed values: `ACTIVE`, `PENDING_ACTIVATION`, `SUSPENDED`, `DISABLED`. A status change revokes existing sessions. Self-disabling the current Super Admin is rejected. Full last-active-Super-Admin protection remains Batch 2.

## Health APIs

### GET `/health`

Legacy liveness compatibility endpoint.

### GET `/api/v1/health`

Legacy API health compatibility endpoint.

### GET `/api/v1/health/live`

Process-liveness only. Returns `200` while the application process can serve requests.

### GET `/api/v1/health/ready`

Returns `200` only when startup bootstrap has no recorded failure and the database, required schema, required auth columns, and Alembic revision are valid. Returns `503` when not ready.

## Explicitly Absent in Batch 1

- `/api/v1/clients...`
- `/api/v1/jobs...`
- Work Station, Audit Engine, Drive, Communication, Staff, Notifications, and AI endpoints
