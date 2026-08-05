import pytest

from scripts.bootstrap_super_admin import BootstrapInput, read_bootstrap_input


def test_bootstrap_input_uses_safe_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOOTSTRAP_LOGIN_ID", raising=False)
    monkeypatch.delenv("BOOTSTRAP_FULL_NAME", raising=False)
    monkeypatch.delenv("BOOTSTRAP_EMAIL", raising=False)
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "TemporaryPass123!")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD_CONFIRM", "TemporaryPass123!")

    result = read_bootstrap_input()

    assert result == BootstrapInput(
        login_id="Admin@001",
        full_name="FAMES & R Super Admin",
        email=None,
        password="TemporaryPass123!",
    )


def test_bootstrap_input_rejects_password_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "TemporaryPass123!")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD_CONFIRM", "DifferentPass123!")

    with pytest.raises(ValueError, match="confirmation"):
        read_bootstrap_input()
