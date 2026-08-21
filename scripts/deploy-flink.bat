@echo off
setlocal
set "ROOT=%~dp0.."
call "%ROOT%\scripts\build-flink.bat"
if errorlevel 1 exit /b 1
pushd "%ROOT%\infra"
terraform init -upgrade
if errorlevel 1 goto :fail
terraform fmt
if errorlevel 1 goto :fail
terraform validate
if errorlevel 1 goto :fail
terraform apply -var="flink_start_application=true"
if errorlevel 1 goto :fail
popd
endlocal
exit /b 0
:fail
popd
endlocal
exit /b 1
