import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.client_models import Client
from app.db import SessionLocal
from app.deps import require_password_changed
from app.document_models import Document, DocumentAccessLog, DocumentVersion
from app.foundation.permissions import Permission, role_has_permission
from app.main import app
from app.models import AuthUser


def _super_admin() -> AuthUser:
    return AuthUser(
        id="test-doc-super-admin",
        login_id="doc-super-admin",
        full_name="Document Super Admin",
        role="SUPER_ADMIN",
        password_hash="x",
        status="ACTIVE",
        must_change_password=False,
    )


def _unassigned_staff() -> AuthUser:
    return AuthUser(
        id="test-doc-unassigned-staff",
        login_id="doc-unassigned-staff",
        full_name="Unassigned Staff",
        role="STAFF",
        password_hash="x",
        status="ACTIVE",
        must_change_password=False,
    )


def test_document_models_and_role_permissions_registered():
    assert Document.__table__.name == "documents"
    assert DocumentVersion.__table__.name == "document_versions"
    assert DocumentAccessLog.__table__.name == "document_access_logs"
    assert role_has_permission("PARTNER", Permission.DOCUMENT_ARCHIVE) is True
    assert role_has_permission("STAFF", Permission.DOCUMENT_UPLOAD) is True
    assert role_has_permission("STAFF", Permission.DOCUMENT_ARCHIVE) is False


def test_private_document_upload_version_download_and_access_control():
    client_id = str(uuid.uuid4())
    client_code = f"FRC-CLI-DOC-{uuid.uuid4().hex[:8].upper()}"
    with SessionLocal() as db:
        db.add(
            Client(
                id=client_id,
                client_code=client_code,
                legal_name="Document API Test Client",
                entity_type="PRIVATE_LIMITED",
                status="ACTIVE",
            )
        )
        db.commit()

    app.dependency_overrides[require_password_changed] = _super_admin
    http = TestClient(app)
    document_id = None
    try:
        created = http.post(
            "/api/v1/documents",
            data={
                "resource_type": "CLIENT",
                "resource_id": client_id,
                "title": "Signed engagement letter",
                "document_type": "ENGAGEMENT_LETTER",
                "confidentiality_level": "CONFIDENTIAL",
            },
            files={"file": ("engagement-letter.txt", b"version-one", "text/plain")},
        )
        assert created.status_code == 201, created.text
        body = created.json()
        document_id = body["id"]
        assert body["current_version"] == 1
        assert body["versions"][0]["version_number"] == 1
        assert len(body["versions"][0]["sha256_hex"]) == 64

        downloaded = http.get(f"/api/v1/documents/{document_id}/versions/1/download")
        assert downloaded.status_code == 200
        assert downloaded.content == b"version-one"
        assert downloaded.headers["cache-control"] == "private, no-store"

        versioned = http.post(
            f"/api/v1/documents/{document_id}/versions",
            data={"expected_version": "1", "change_note": "Signed replacement"},
            files={"file": ("engagement-letter-v2.txt", b"version-two", "text/plain")},
        )
        assert versioned.status_code == 200, versioned.text
        assert versioned.json()["current_version"] == 2

        stale = http.post(
            f"/api/v1/documents/{document_id}/versions",
            data={"expected_version": "1"},
            files={"file": ("stale.txt", b"stale", "text/plain")},
        )
        assert stale.status_code == 409
        assert stale.json()["error"]["code"] == "VERSION_CONFLICT"

        access_log = http.get(f"/api/v1/documents/{document_id}/access-log")
        assert access_log.status_code == 200
        actions = {row["action"] for row in access_log.json()}
        assert {"UPLOAD", "DOWNLOAD", "VERSION_UPLOAD"}.issubset(actions)

        app.dependency_overrides[require_password_changed] = _unassigned_staff
        denied = http.get(f"/api/v1/documents/{document_id}/versions/2/download")
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "DOCUMENT_ACCESS_DENIED"
    finally:
        app.dependency_overrides.clear()
        with SessionLocal() as db:
            if document_id:
                version_ids = list(db.scalars(select(DocumentVersion.id).where(DocumentVersion.document_id == document_id)))
                db.execute(delete(DocumentAccessLog).where(DocumentAccessLog.document_id == document_id))
                if version_ids:
                    db.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
                db.execute(delete(Document).where(Document.id == document_id))
            db.execute(delete(Client).where(Client.id == client_id))
            db.commit()
