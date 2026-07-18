# FAMES & R Office PRO — Backend

FastAPI backend for FAMES & R Office PRO.

## Phase 1: Custom Login/Auth

This backend owns authentication directly. Supabase Auth is not required for login.

Implemented:
- Login ID + password authentication
- Argon2 password hashing
- JWT access tokens
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/change-password`
- Failed-login lockout
- Auth audit log
- Super Admin user creation and account status controls
- One-time environment-driven bootstrap script

## Local run

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .[dev]
cp .env.example .env
uvicorn app.main:app --reload
```

Health:
- `/health`
- `/api/v1/health`

## Bootstrap first users

Set only the password environment variables you want to bootstrap, then run:

```bash
python -m scripts.bootstrap_users
```

Passwords are never stored in source code. Each bootstrapped account is forced to change its temporary password after first login.

## Production requirements

Set a PostgreSQL `DATABASE_URL`, a strong random `JWT_SECRET`, and the allowed frontend origin(s). Do not commit `.env` or production credentials.
