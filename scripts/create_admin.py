#!/usr/bin/env python3
"""
Local administrative script for creating administrator accounts.

Security enforcement:
- Local script only; not accessible through public web APIs.
- Interactive by default; supports command-line arguments for automated setup.
- Enforces strict input validation: minimum length, valid characters, matching confirmation.
- Case-insensitively checks for existing users to prevent overwriting or elevation.
- Uses Argon2 password hashing with high work factor.
"""

import argparse
import getpass
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.security.password_hashing import hash_password
from app.services.json_storage import read_records, write_records

USERNAME_REGEX = re.compile(r"^[A-Za-z0-9_.-]+$")


def create_admin_user(username: str, password: str, display_name: str = "Administrator") -> dict:
    """Creates a local admin account with validation and safety checks."""
    username = username.strip()
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters")
    if not USERNAME_REGEX.match(username):
        raise ValueError("Username contains invalid characters (allowed: letters, digits, _, ., -)")

    if len(password) < 10:
        raise ValueError("Password must be at least 10 characters")

    users = read_records("users")
    if any(u.get("username", "").lower() == username.lower() for u in users):
        raise ValueError(f"Username '{username}' already exists. Cannot overwrite or elevate existing accounts.")

    admin_user = {
        "id": str(uuid.uuid4()),
        "username": username,
        "display_name": display_name.strip() or "Administrator",
        "role": "admin",
        "password_hash": hash_password(password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suspended": False,
    }
    users.append(admin_user)
    write_records("users", users)
    return {k: v for k, v in admin_user.items() if k != "password_hash"}


def main():
    parser = argparse.ArgumentParser(description="Create a local administrator account.")
    parser.add_argument("--username", help="Administrator username (minimum 3 characters)")
    parser.add_argument("--password", help="Administrator password (minimum 10 characters)")
    parser.add_argument("--display-name", default="Administrator", help="Administrator display name")
    args = parser.parse_args()

    try:
        username = args.username
        if not username:
            username = input("Admin username (3+ chars): ").strip()

        password = args.password
        if not password:
            password = getpass.getpass("Admin password (10+ chars): ")
            confirm = getpass.getpass("Confirm password: ")
            if password != confirm:
                raise ValueError("Passwords do not match")

        display_name = args.display_name or "Administrator"
        result = create_admin_user(username, password, display_name)
        print(f"Administrator '{result['username']}' created successfully (ID: {result['id']}).")
        return 0
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
