"""Create a doctor account interactively: python -m app.create_doctor EMAIL NAME."""

from __future__ import annotations

import getpass
import sys

from sqlalchemy.exc import IntegrityError

from .auth import hash_password
from .database import SessionLocal, init_db
from .models import User


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python -m app.create_doctor EMAIL NAME")
        return 2

    email, name = sys.argv[1].strip().lower(), sys.argv[2].strip()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1] or not name:
        print("Provide a valid email address and non-empty name.")
        return 2
    password = getpass.getpass("Doctor password (minimum 12 characters): ")
    if len(password) < 12:
        print("Password must be at least 12 characters.")
        return 2

    init_db()
    db = SessionLocal()
    try:
        db.add(User(email=email, name=name, role="doctor", password_hash=hash_password(password)))
        db.commit()
    except IntegrityError:
        db.rollback()
        print("An account with that email already exists.")
        return 1
    finally:
        db.close()
    print(f"Doctor account created for {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
