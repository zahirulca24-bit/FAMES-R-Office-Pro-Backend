import os

from sqlalchemy import func, select

from app.db import Base, SessionLocal, engine
from app.models import AuthUser
from app.security import hash_password


USERS = [
    ("Admin@001", "zahirul.ca24@gmail.com", "FAMES & R Super Admin", "SUPER_ADMIN", "BOOTSTRAP_ADMIN_PASSWORD", "ACTIVE"),
    ("Manager@001", "manager.fames@gmail.com", "FAMES & R Manager", "MANAGER", "BOOTSTRAP_MANAGER_PASSWORD", "ACTIVE"),
    ("AssistantDev@001", "Nayan.macrom@gmail.com", "Nayan", "ASSISTANT_DEVELOPER", "BOOTSTRAP_ASSISTANT_DEVELOPER_PASSWORD", "ACTIVE"),
    ("Student@001", "bayazidmridha6@gmail.com", "Bayazid", "STUDENT", "BOOTSTRAP_STUDENT_001_PASSWORD", "ACTIVE"),
    ("Student@002", "iftekhairul2000@gmail.com", "Iftekhar", "STUDENT", "BOOTSTRAP_STUDENT_002_PASSWORD", "ACTIVE"),
    ("Student@003", "tanjumaktertisha665@gmail.com", "Tanjum", "STUDENT", "BOOTSTRAP_STUDENT_003_PASSWORD", "ACTIVE"),
    ("Student@004", "hemadryroy44@gmail.com", "Hemadry", "STUDENT", "BOOTSTRAP_STUDENT_004_PASSWORD", "ACTIVE"),
    ("Shafi@001", os.getenv("BOOTSTRAP_PARTNER_EMAIL") or None, "Mr. Shafi Uddin Ahmed, FCA", "PARTNER", "BOOTSTRAP_PARTNER_PASSWORD", "PENDING_ACTIVATION"),
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        for login_id, email, full_name, role, password_env, status in USERS:
            password = os.getenv(password_env)
            if not password:
                print(f"SKIP {login_id}: {password_env} is not set")
                continue
            if len(password) < 10:
                print(f"SKIP {login_id}: {password_env} must be at least 10 characters")
                continue

            try:
                user = db.scalar(select(AuthUser).where(func.lower(AuthUser.login_id) == login_id.lower()))
                password_hash = hash_password(password)
                if user is None:
                    user = AuthUser(
                        login_id=login_id,
                        email=email,
                        full_name=full_name,
                        role=role,
                        password_hash=password_hash,
                        status=status,
                        must_change_password=True,
                    )
                    db.add(user)
                    print(f"CREATE {login_id}")
                else:
                    user.email = email
                    user.full_name = full_name
                    user.role = role
                    user.password_hash = password_hash
                    user.status = status
                    user.must_change_password = True
                    print(f"UPDATE {login_id}")
                db.commit()
            except Exception as exc:
                db.rollback()
                print(f"BOOTSTRAP ERROR {login_id}: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
