@echo off
setlocal

set "ROOT=%~dp0.."
set "INFRA=%ROOT%\infra"

call "%ROOT%\scripts\build-flink.bat"
if errorlevel 1 exit /b 1

where terraform >nul 2>nul
if errorlevel 1 (
  echo ERROR: Terraform이 필요합니다.
  exit /b 1
)

pushd "%INFRA%"

echo [1/4] terraform init -upgrade
terraform init -upgrade
if errorlevel 1 goto :fail

echo [2/4] terraform fmt
terraform fmt
if errorlevel 1 goto :fail

echo [3/4] terraform validate
terraform validate
if errorlevel 1 goto :fail

echo [4/4] terraform apply
terraform apply
if errorlevel 1 goto :fail

popd
endlocal
exit /b 0

:fail
popd
endlocal
exit /b 1
