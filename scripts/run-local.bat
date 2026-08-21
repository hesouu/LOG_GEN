@echo off
setlocal EnableExtensions
chcp 65001 >nul

rem Usage:
rem   run-local.bat [DOMAIN] [DURATION_SECONDS] [BASE_RPS] [CORRUPTION_RATE] [OUTPUT_MODE] [TIME_SCALE]

set "DOMAIN=%~1"
if not defined DOMAIN set "DOMAIN=ecommerce"
set "DURATION_SECONDS=%~2"
if not defined DURATION_SECONDS set "DURATION_SECONDS=30"
set "BASE_RPS=%~3"
if not defined BASE_RPS set "BASE_RPS=2.0"
set "CORRUPTION_RATE=%~4"
if not defined CORRUPTION_RATE set "CORRUPTION_RATE=0.03"
set "OUTPUT_MODE=%~5"
if not defined OUTPUT_MODE set "OUTPUT_MODE=both"
set "TIME_SCALE=%~6"
if not defined TIME_SCALE set "TIME_SCALE=1.0"

call :validate_domain
if errorlevel 1 exit /b 1

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "GENERATOR=%ROOT%\generator"
set "OUTPUT=%ROOT%\output"
if not exist "%OUTPUT%" mkdir "%OUTPUT%"
set "LOG_FILE=%OUTPUT%\%DOMAIN%-%RANDOM%%RANDOM%.jsonl"
set "RUN_ID=local-%RANDOM%%RANDOM%"

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found.
  exit /b 1
)

python -c "import faker" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Faker is not installed.
  echo         python -m pip install -r "%GENERATOR%\requirements.txt"
  exit /b 1
)

echo.
echo Domain          : %DOMAIN%
echo Duration        : %DURATION_SECONDS%s
echo Base RPS        : %BASE_RPS%
echo Corruption rate : %CORRUPTION_RATE%
echo Output mode     : %OUTPUT_MODE%
echo Time scale      : %TIME_SCALE%
echo Log file        : %LOG_FILE%
echo.

pushd "%GENERATOR%"
python -m app.main
set "RC=%ERRORLEVEL%"
popd

if "%OUTPUT_MODE%"=="file" echo Generated log: %LOG_FILE%
if "%OUTPUT_MODE%"=="both" echo Generated log: %LOG_FILE%
exit /b %RC%

:validate_domain
if /I "%DOMAIN%"=="ecommerce" exit /b 0
if /I "%DOMAIN%"=="finance" exit /b 0
if /I "%DOMAIN%"=="smartfactory" exit /b 0
if /I "%DOMAIN%"=="game" exit /b 0
echo [ERROR] DOMAIN must be ecommerce, finance, smartfactory, or game.
exit /b 1
