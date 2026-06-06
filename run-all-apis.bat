@echo off
REM Start all 7 APIs in separate windows
setlocal
where python >nul 2>&1 || (echo Install Python 3.12+ first & pause & exit /b 1)
if not exist "%TEMP%\jwt-keys" mkdir "%TEMP%\jwt-keys"

echo Installing all API deps (first run only)...
for %%A in (auth-api user-api billing-api live-api social-api notification-api analytics-api) do (
  cd %%A
  python -m pip install -q -r requirements.txt
  cd ..
)

start "auth-api 8001"        cmd /k "cd auth-api        && set JWT_KEY_DIR=%TEMP%\jwt-keys && set DEV_MODE=true && python -m uvicorn app.main:app --host 127.0.0.1 --port 8001"
timeout /t 3 /nobreak >nul
start "user-api 8002"        cmd /k "cd user-api        && set JWT_PUBLIC_KEY_URL=http://127.0.0.1:8001/.well-known/jwks.json && python -m uvicorn main:app --host 127.0.0.1 --port 8002"
start "billing-api 8012"     cmd /k "cd billing-api     && python -m uvicorn main:app --host 127.0.0.1 --port 8012"
start "live-api 8013"        cmd /k "cd live-api        && python -m uvicorn main:app --host 127.0.0.1 --port 8013"
start "social-api 8014"      cmd /k "cd social-api      && python -m uvicorn main:app --host 127.0.0.1 --port 8014"
start "notification-api 8015" cmd /k "cd notification-api && python -m uvicorn main:app --host 127.0.0.1 --port 8015"
start "analytics-api 8016"   cmd /k "cd analytics-api   && python -m uvicorn main:app --host 127.0.0.1 --port 8016"

echo.
echo All 7 APIs starting. Open these in your browser:
echo   http://127.0.0.1:8001/docs  (auth)
echo   http://127.0.0.1:8002/docs  (user)
echo   http://127.0.0.1:8012/docs  (billing)
echo   http://127.0.0.1:8013/docs  (live)
echo   http://127.0.0.1:8014/docs  (social)
echo   http://127.0.0.1:8015/docs  (notification)
echo   http://127.0.0.1:8016/docs  (analytics)
echo.
pause
