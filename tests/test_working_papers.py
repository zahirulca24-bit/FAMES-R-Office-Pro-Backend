import uuid

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.client_models import Client
from app.db import SessionLocal
from app.deps import require_password_changed
from app.document_models import Document, DocumentVersion
from app.engagement_models import Engagement
from app.main import app
from app.models import ActivityEvent, AuditEvent, AuthUser
from app.working_paper_models import WorkingPaper, WorkingPaperEvidence, WorkingPaperReviewNote, WorkingPaperSignoff


def test_working_paper_evidence_review_signoff_and_lock_flow():
    suffix = uuid.uuid4().hex[:8]
    user_id = str(uuid.uuid4())
    client_id = str(uuid.uuid4())
    engagement_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    document_version_id = str(uuid.uuid4())

    user = AuthUser(
        id=user_id,
        login_id=f"wp-admin-{suffix}",
        full_name="Working Paper Admin",
        role="SUPER_ADMIN",
        password_hash="x",
        status="ACTIVE",
        must_change_password=False,
    )

    with SessionLocal() as db:
        db.add(user)
        db.add(Client(id=client_id, client_code=f"FRC-CLI-WP-{suffix}", legal_name="Working Paper Test Client", entity_type="PRIVATE_LIMITED", status="ACTIVE"))
        db.flush()
        db.add(
            Engagement(
                id=engagement_id,
                engagement_code=f"FRC-ENG-WP-{suffix}",
                client_id=client_id,
                service_type="AUDIT",
                title="Working Paper Test Engagement",
                partner_user_id=user_id,
            )
        )
        db.flush()
        db.add(
            Document(
                id=document_id,
                document_code=f"FRC-DOC-WP-{suffix}",
                resource_type="ENGAGEMENT",
                resource_id=engagement_id,
                title="Audit evidence",
                document_type="EVIDENCE",
                current_version=1,
                created_by_user_id=user_id,
            )
        )
        db.flush()
        db.add(
            DocumentVersion(
                id=document_version_id,
                document_id=document_id,
                version_number=1,
                original_filename="evidence.txt",
                content_type="text/plain",
                size_bytes=8,
                sha256_hex="0" * 64,
                content_bytes=b"evidence",
                uploaded_by_user_id=user_id,
            )
        )
        db.commit()

    app.dependency_overrides[require_password_changed] = lambda: user
    http = TestClient(app)
    paper_id = None
    note_id = None
    try:
        created = http.post(
            "/api/v1/working-papers",
            json={
                "engagement_id": engagement_id,
                "paper_code": "A-100",
                "title": "Cash and bank testing",
                "area": "CASH",
                "objective": "Verify existence and accuracy",
                "conclusion": "No material exception noted",
            },
        )
        assert created.status_code == 201, created.text
        paper_id = created.json()["id"]
        assert created.json()["status"] == "DRAFT"
        assert created.json()["version"] == 1

        evidence = http.post(
            f"/api/v1/working-papers/{paper_id}/evidence",
            json={
                "document_id": document_id,
                "document_version_id": document_version_id,
                "expected_version": 1,
                "evidence_role": "PRIMARY",
                "assertion": "EXISTENCE",
            },
        )
        assert evidence.status_code == 201, evidence.text

        note = http.post(f"/api/v1/working-papers/{paper_id}/review-notes", json={"note_text": "Please document the bank confirmation cross-reference."})
        assert note.status_code == 201, note.text
        note_id = note.json()["id"]
        assert note.json()["status"] == "OPEN"

        submitted = http.post(f"/api/v1/working-papers/{paper_id}/submit", json={"expected_version": 3, "comment": "Prepared for review"})
        assert submitted.status_code == 200, submitted.text
        assert submitted.json()["status"] == "SUBMITTED"

        reviewed = http.post(f"/api/v1/working-papers/{paper_id}/review", json={"expected_version": 4, "comment": "Review completed subject to note"})
        assert reviewed.status_code == 200, reviewed.text
        assert reviewed.json()["status"] == "REVIEWED"

        blocked = http.post(f"/api/v1/working-papers/{paper_id}/approve", json={"expected_version": 5})
        assert blocked.status_code == 409
        assert blocked.json()["error"]["code"] == "OPEN_REVIEW_NOTES"

        resolved = http.post(
            f"/api/v1/working-papers/{paper_id}/review-notes/{note_id}/resolve",
            json={"expected_version": 5, "resolution_note": "Cross-reference added to the working paper."},
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["status"] == "RESOLVED"

        approved = http.post(f"/api/v1/working-papers/{paper_id}/approve", json={"expected_version": 6, "comment": "Approved"})
        assert approved.status_code == 200, approved.text
        assert approved.json()["status"] == "APPROVED"

        locked = http.post(f"/api/v1/working-papers/{paper_id}/lock", json={"expected_version": 7, "comment": "Final lock"})
        assert locked.status_code == 200, locked.text
        assert locked.json()["status"] == "LOCKED"
        assert locked.json()["is_locked"] is True

        edit_locked = http.patch(f"/api/v1/working-papers/{paper_id}", json={"expected_version": 8, "conclusion": "Changed after lock"})
        assert edit_locked.status_code == 409
        assert edit_locked.json()["error"]["code"] == "WORKING_PAPER_LOCKED"

        history = http.get(f"/api/v1/working-papers/{paper_id}/history")
        assert history.status_code == 200
        assert [row["action"] for row in history.json()] == ["PREPARED", "SUBMITTED", "REVIEWED", "APPROVED", "LOCKED"]
    finally:
        app.dependency_overrides.clear()
        with SessionLocal() as db:
            if paper_id:
                db.execute(delete(WorkingPaperSignoff).where(WorkingPaperSignoff.working_paper_id == paper_id))
                db.execute(delete(WorkingPaperReviewNote).where(WorkingPaperReviewNote.working_paper_id == paper_id))
                db.execute(delete(WorkingPaperEvidence).where(WorkingPaperEvidence.working_paper_id == paper_id))
                db.execute(delete(WorkingPaper).where(WorkingPaper.id == paper_id))
                db.execute(delete(ActivityEvent).where(ActivityEvent.resource_type == "WORKING_PAPER", ActivityEvent.resource_id == paper_id))
                db.execute(delete(AuditEvent).where(AuditEvent.resource_type == "WORKING_PAPER", AuditEvent.resource_id == paper_id))
            db.execute(delete(DocumentVersion).where(DocumentVersion.id == document_version_id))
            db.execute(delete(Document).where(Document.id == document_id))
            db.execute(delete(Engagement).where(Engagement.id == engagement_id))
            db.execute(delete(Client).where(Client.id == client_id))
            db.execute(delete(AuthUser).where(AuthUser.id == user_id))
            db.commit()
