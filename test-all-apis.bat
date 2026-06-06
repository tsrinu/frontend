@echo off
REM Run every API's tests in isolation
setlocal
set PASS=0
set FAIL=0

where python >nul 2>&1 || (echo Install Python 3.12+ first & pause & exit /b 1)

echo Installing test deps...
python -m pip install -q -r tests\requirements.txt

for %%A in (auth-api user-api billing-api live-api social-api notification-api analytics-api) do (
  echo.
  echo ============================================
  echo  %%A
  echo ============================================
  cd %%A
  python -m pip install -q -r requirements.txt
  python -m pytest tests\ -q --tb=line
  cd ..
)
echo.
echo Done. See per-API output above.
pause
