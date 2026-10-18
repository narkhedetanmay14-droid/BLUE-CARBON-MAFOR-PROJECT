$username = "demo_admin"
$password = "BlueCarbonDemo@2026!"

# Create the input
$input = "$username`n$password`n$password"

# Run the script with input piped
$input | & "C:\Users\ASUS\Desktop\BLUE-CARBON-REGISTRATION-AND-MONITORING\.venv\Scripts\python.exe" "C:\Users\ASUS\Desktop\BLUE-CARBON-REGISTRATION-AND-MONITORING\scripts\create_admin.py"
