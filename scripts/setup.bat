@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul

rem ============================================================
rem Fargate Synthetic Log Generator - AWS Setup
rem Usage: setup.bat [REGION]
rem ============================================================

set "REGION=%~1"
if not defined REGION set "REGION=ap-northeast-2"

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "INFRA=%ROOT%\infra"
set "GENERATOR=%ROOT%\generator"

call :require_cmd aws
if errorlevel 1 exit /b 1
call :require_cmd terraform
if errorlevel 1 exit /b 1
call :require_cmd docker
if errorlevel 1 exit /b 1

echo.
echo [1/4] Terraform init
terraform -chdir="%INFRA%" init
if errorlevel 1 goto :fail

echo.
echo [2/4] Terraform apply
terraform -chdir="%INFRA%" apply -auto-approve -var="aws_region=%REGION%"
if errorlevel 1 goto :fail

rem Read Terraform output via a temp file. This is more reliable on Windows CMD
rem than executing terraform -chdir inside FOR /F command substitution.
call :tf_output_raw ecr_repository_url REPO
if errorlevel 1 (
  echo [ERROR] Terraform output 'ecr_repository_url' not found.
  echo [INFO] Try manually: terraform -chdir="%INFRA%" output -raw ecr_repository_url
  exit /b 1
)

for /f "tokens=1 delims=/" %%A in ("%REPO%") do set "REGISTRY=%%A"

echo.
echo [INFO] ECR repository : %REPO%
echo [INFO] ECR registry   : %REGISTRY%

echo.
echo [3/4] ECR login
aws ecr get-login-password --region "%REGION%" | docker login --username AWS --password-stdin "%REGISTRY%"
if errorlevel 1 goto :fail

echo.
echo [4/4] Build and push Python/Faker generator image
docker build --no-cache --platform linux/amd64 -t "%REPO%:latest" "%GENERATOR%"
if errorlevel 1 goto :fail

docker push "%REPO%:latest"
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo Setup completed successfully.
echo ============================================================
echo Example:
echo   scripts\run-generator.bat ecommerce 300 2.0 0.03
exit /b 0

:tf_output_raw
set "TF_OUTPUT_NAME=%~1"
set "TF_OUTPUT_FILE=%TEMP%\loggen-tf-%RANDOM%-%RANDOM%.txt"
terraform -chdir="%INFRA%" output -raw "%TF_OUTPUT_NAME%" > "%TF_OUTPUT_FILE%" 2>nul
if errorlevel 1 (
  del /q "%TF_OUTPUT_FILE%" >nul 2>&1
  exit /b 1
)
set "TF_OUTPUT_VALUE="
set /p "TF_OUTPUT_VALUE="<"%TF_OUTPUT_FILE%"
del /q "%TF_OUTPUT_FILE%" >nul 2>&1
if not defined TF_OUTPUT_VALUE exit /b 1
set "%~2=%TF_OUTPUT_VALUE%"
exit /b 0

:require_cmd
where %~1 >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Command not found: %~1
  exit /b 1
)
exit /b 0

:fail
echo.
echo [ERROR] Setup failed. Check the command output above.
exit /b 1
