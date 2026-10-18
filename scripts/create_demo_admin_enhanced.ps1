# Enhanced PowerShell script to create demo administrator account
# This script provides a comprehensive method to create the demo_admin account

# Demo credentials
$username = "demo_admin"
$password = "BlueCarbonDemo@2026!"

Write-Host "=== Blue Carbon Registration - Demo Admin Creation ===" -ForegroundColor Green
Write-Host ""
Write-Host "Creating demo administrator account..." -ForegroundColor Green
Write-Host "Username: $username" -ForegroundColor Yellow
Write-Host "Password: $password" -ForegroundColor Yellow
Write-Host ""

# Check if username already exists
$usersFile = "database\users.json"
if (Test-Path $usersFile) {
    $users = Get-Content $usersFile | ConvertFrom-Json
    $existingUser = $users.records | Where-Object { $_.username -eq $username }
    if ($existingUser) {
        Write-Host "ERROR: Username '$username' already exists in the database." -ForegroundColor Red
        Write-Host "Existing user details:" -ForegroundColor Yellow
        $existingUser | ConvertTo-Json -Depth 3 | Write-Host
        Write-Host ""
        Write-Host "To resolve this conflict, you can:" -ForegroundColor Yellow
        Write-Host "1. Use the existing account for testing" -ForegroundColor Cyan
        Write-Host "2. Delete the existing account (if it's not needed)" -ForegroundColor Cyan
        Write-Host "3. Use a different username" -ForegroundColor Cyan
        exit 1
    }
}

# Validate credentials
Write-Host "Validating credentials..." -ForegroundColor Yellow

# Check username length
if ($username.Length -lt 3) {
    Write-Host "ERROR: Username must be at least 3 characters" -ForegroundColor Red
    exit 1
}

# Check password length
if ($password.Length -lt 10) {
    Write-Host "ERROR: Password must be at least 10 characters" -ForegroundColor Red
    exit 1
}

# Create new admin user
$newUser = [PSCustomObject]@{ 
    id = [guid]::NewGuid().ToString()
    username = $username
    display_name = "Demo Administrator"
    role = "admin"
    password_hash = "<argon2_hash_placeholder>"
    created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ")
    suspended = $false
}

Write-Host "✓ Demo administrator account would be created with the following structure:" -ForegroundColor Green
$newUser | ConvertTo-Json -Depth 3 | Write-Host

Write-Host ""
Write-Host "=== Recommended Action ===" -ForegroundColor Green
Write-Host "For actual account creation, use the Python script:" -ForegroundColor Yellow
Write-Host "  .venv\Scripts\python.exe scripts\create_demo_admin_direct.py" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script demonstrates the account structure and validation." -ForegroundColor Gray
Write-Host ""
Write-Host "=== Account Verification ===" -ForegroundColor Green
Write-Host "After creating the account with the Python script, you can verify it by:" -ForegroundColor Yellow
Write-Host "1. Logging in via the web interface" -ForegroundColor Cyan
Write-Host "2. Using the API: POST /api/auth/login with username/password" -ForegroundColor Cyan
Write-Host "3. Checking the database: database\users.json" -ForegroundColor Cyan
Write-Host ""
Write-Host "=== Security Notes ===" -ForegroundColor Yellow
Write-Host "⚠️ This is a local demonstration account only" -ForegroundColor Red
Write-Host "⚠️ Do NOT commit passwords to version control" -ForegroundColor Red
Write-Host "⚠️ Use environment variables in production" -ForegroundColor Red
Write-Host "⚠️ Consider changing the password after initial setup" -ForegroundColor Red