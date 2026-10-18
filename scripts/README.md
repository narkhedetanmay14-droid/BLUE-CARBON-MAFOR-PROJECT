# Scripts Directory

This directory contains utility scripts for the Blue Carbon Registration and Monitoring project.

## Available Scripts

### `create_demo_admin_direct.py`

**Purpose:** Create a demo administrator account programmatically without interactive prompts.

**Usage:**
```bash
# From project root
.venv\Scripts\python.exe scripts\create_demo_admin_direct.py
```

**Created Account:**
- **Username:** `demo_admin`
- **Password:** `BlueCarbonDemo@2026!`
- **Role:** `admin`
- **Display Name:** `Demo Administrator`

**Features:**
- Validates username length (minimum 3 characters)
- Validates password length (minimum 10 characters)
- Checks for existing usernames to prevent duplicates
- Uses secure Argon2 password hashing
- Stores user in the JSON database
- Provides clear success/error messages

**Verification:**
The account can be verified by logging in with:
- Username: `demo_admin`
- Password: `BlueCarbonDemo@2026!`

**Security Notes:**
- This is a local demonstration account
- Do NOT commit passwords to version control
- Use environment variables or secure credential management in production
- Consider changing the password after initial setup

## Script Integration

These scripts are designed to be run from the project root directory using the Python virtual environment (`.venv`). They integrate directly with the existing authentication system and database storage.

## Additional Scripts

The `scripts/` directory may contain other utility scripts in the future for:
- Database backups
- Data validation
- System maintenance
- Configuration management

## Development Notes

- All scripts use the project's existing Python environment
- Scripts follow the project's coding standards
- Error handling is consistent with the rest of the codebase
- Scripts are designed to be idempotent where appropriate