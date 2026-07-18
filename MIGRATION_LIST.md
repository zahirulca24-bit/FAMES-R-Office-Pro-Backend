# Batch 1 Migration List

## Alembic Revision `20260719_01`

File: `migrations/versions/20260719_01_batch1_auth_baseline.py`

Purpose:

- Establish Alembic ownership of the existing authentication schema.
- Create `auth_users` and `auth_audit_logs` on a fresh database.
- Adopt a pre-Alembic database without recreating existing auth tables.
- Add non-null `auth_users.token_version` with default `0` when absent.
- Create required auth lookup/audit indexes when absent.
- Support PostgreSQL offline SQL generation for a fresh database.

Revision graph:

```text
<base> -> 20260719_01 (head)
```

Downgrade policy:

The revision is intentionally non-downgradable. It may adopt tables created before Alembic; automatically dropping those tables would risk destructive data loss. Recovery must use a verified database backup and a reviewed forward migration.

Verification performed:

- Fresh SQLite upgrade to head
- `alembic heads` and `alembic current`
- Upgrade of a legacy create-all-style SQLite database
- Presence of `token_version` after legacy upgrade
- PostgreSQL-dialect offline SQL generation

Not performed:

- Live PostgreSQL migration against the production or staging database
- Render deployment
