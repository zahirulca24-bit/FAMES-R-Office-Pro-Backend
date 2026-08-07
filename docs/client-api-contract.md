# Client API Contract

Base path: `/api/v1/clients`

All endpoints require an authenticated user whose initial password-change requirement has been cleared. Client operations are additionally checked against the backend permission catalogue and portfolio ownership. The frontend must not treat hidden controls as authorization.

## Endpoints

- `POST /api/v1/clients` — create a client aggregate with contacts, addresses, identifiers and partner/manager ownership.
- `GET /api/v1/clients` — paginated client list. Supports `q`, `status`, `include_archived`, `page`, `page_size`.
- `GET /api/v1/clients/{client_id}` — client detail with linked contacts, addresses and identifiers.
- `PATCH /api/v1/clients/{client_id}` — update master fields. `expected_version` is mandatory for optimistic concurrency.
- `POST /api/v1/clients/{client_id}/archive` — controlled archive. `reason` and `expected_version` are mandatory and lifecycle rules are enforced.
- `GET /api/v1/clients/{client_id}/activity` — user-facing activity timeline.
- `GET /api/v1/clients/export` — permission-controlled CSV export.

## Frontend handling rules

- Persist server-issued `id`, `client_code`, `status` and `version`; do not create parallel browser-only truth.
- On `VERSION_CONFLICT`, reload the record before allowing another update.
- On `CLIENT_ACCESS_DENIED` or `PERMISSION_DENIED`, show a denied state rather than retrying.
- On `CLIENT_DUPLICATE_IDENTIFIER`, keep the form values and ask the user to correct the identifier.
- Archived clients are omitted by default and must not be editable.
- Preserve and surface the `X-Correlation-ID` when reporting API failures.
- Refresh/list/detail views must come from backend persistence, not mock or in-memory state.

## Error envelope

Controlled API errors use the shared structure:

```json
{
  "success": false,
  "error": {
    "code": "VERSION_CONFLICT",
    "message": "Client record has changed; reload before updating",
    "details": {}
  },
  "meta": {
    "correlation_id": "..."
  }
}
```
