#!/usr/bin/env python3
"""
Direct admin account creation script for Blue Carbon Registration and Monitoring.
This bypasses the interactive prompts and creates the account programmatically.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.json_storage import read_records, write_records
from app.security.password_hashing import hash_password
import uuid
from datetime import datetime, timezone

# Demo credentials
USERNAME = "demo_admin"
PASSWORD = "BlueCarbonDemo@2026!"
DISPLAY_NAME = "Demo Administrator"
ROLE = "admin"

def create_admin():
    """Create an admin account with the specified credentials."""
    
    # Validate inputs
    if len(USERNAME) < 3:
        print("ERROR: Username must be at least 3 characters")
        return False
    
    if len(PASSWORD) < 10:
        print("ERROR: Password must be at least 10 characters")
        return False
    
    # Read existing users
    users = read_records("users")
    
    # Check if username already exists
    if any(u["username"].lower() == USERNAME.lower() for u in users):
        print(f"ERROR: Username '{USERNAME}' already exists")
        return False
    
    # Create new admin user
    new_user = {
        "id": str(uuid.uuid4()),
        "username": USERNAME,
        "display_name": DISPLAY_NAME,
        "role": ROLE,
        "password_hash": hash_password(PASSWORD),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "suspended": False
    }
    
    # Add to users and write
    users.append(new_user)
    write_records("users", users)
    
    print(f"✓ Administrator account created successfully")
    print(f"  Username: {USERNAME}")
    print(f"  Display name: {DISPLAY_NAME}")
    print(f"  Role: {ROLE}")
    return True

if __name__ == "__main__":
    try:
        if create_admin():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
