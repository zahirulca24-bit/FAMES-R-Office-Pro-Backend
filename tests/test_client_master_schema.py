import pytest
from sqlalchemy.exc import IntegrityError

from app.client_models import (
    Client,
    ClientAddress,
    ClientContact,
    ClientDirector,
    ClientIdentifier,
    ClientRelationship,
    ClientShareholder,
    ClientStatusHistory,
)
from app.db import SessionLocal


def _client(code: str, name: str) -> Client:
    return Client(client_code=code, legal_name=name, entity_type="PRIVATE_LIMITED")


def test_client_master_tables_are_registered():
    expected = {
        "clients",
        "client_contacts",
        "client_addresses",
        "client_identifiers",
        "client_directors",
        "client_shareholders",
        "client_relationships",
        "client_status_history",
    }
    table_names = {
        Client.__table__.name,
        ClientContact.__table__.name,
        ClientAddress.__table__.name,
        ClientIdentifier.__table__.name,
        ClientDirector.__table__.name,
        ClientShareholder.__table__.name,
        ClientRelationship.__table__.name,
        ClientStatusHistory.__table__.name,
    }
    assert table_names == expected


def test_client_code_is_unique():
    with SessionLocal() as db:
        first = _client("FRC-CLI-000001", "Alpha Limited")
        db.add(first)
        db.commit()

        db.add(_client("FRC-CLI-000001", "Beta Limited"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        db.delete(first)
        db.commit()


def test_identifier_is_unique_across_clients_by_type_and_normalized_value():
    with SessionLocal() as db:
        first = _client("FRC-CLI-000002", "Gamma Limited")
        second = _client("FRC-CLI-000003", "Delta Limited")
        db.add_all([first, second])
        db.flush()

        db.add(
            ClientIdentifier(
                client_id=first.id,
                identifier_type="TIN",
                value="123-456-789",
                normalized_value="123456789",
            )
        )
        db.commit()

        db.add(
            ClientIdentifier(
                client_id=second.id,
                identifier_type="TIN",
                value="123456789",
                normalized_value="123456789",
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        db.query(ClientIdentifier).filter(ClientIdentifier.client_id == first.id).delete()
        db.delete(first)
        db.delete(second)
        db.commit()


def test_linked_records_reference_client_with_cascade_delete():
    for model in (ClientContact, ClientAddress, ClientIdentifier, ClientDirector, ClientShareholder, ClientStatusHistory):
        fk = next(iter(model.__table__.c.client_id.foreign_keys))
        assert fk.target_fullname == "clients.id"
        assert fk.ondelete == "CASCADE"

    source_fk = next(iter(ClientRelationship.__table__.c.source_client_id.foreign_keys))
    target_fk = next(iter(ClientRelationship.__table__.c.target_client_id.foreign_keys))
    assert source_fk.ondelete == "CASCADE"
    assert target_fk.ondelete == "CASCADE"


def test_client_defaults_support_controlled_lifecycle():
    client = _client("FRC-CLI-000004", "Epsilon Limited")
    assert client.status is None or client.status == "PROSPECT"
    # SQLAlchemy column defaults are applied on insert; the schema contract itself is authoritative.
    assert Client.__table__.c.status.default.arg == "PROSPECT"
    assert Client.__table__.c.version.default.arg == 1
    assert Client.__table__.c.is_archived.default.arg is False
