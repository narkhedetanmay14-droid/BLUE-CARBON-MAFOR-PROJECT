@echo off
setlocal
if not exist "backend\.venv\Scripts\python.exe" (
  cd backend
  set PYTHONPATH=.

  echo Backend venv missing. Follow README.md setup steps first.
  pause
  exit /b 1
)
start "Blue Carbon API" cmd /k "cd /d %~dp0backend && set PYTHONPATH=. && .venv\Scripts\python.exe -m uvicorn app.main:app --reload"
if not exist "frontend\node_modules" (
  echo Frontend dependencies missing. Run npm install in frontend first.
  pause
  exit /b 1
)
start "Blue Carbon Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
endlocal
