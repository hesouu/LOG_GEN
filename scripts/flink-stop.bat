@echo off
setlocal
pushd "%~dp0..\infra"
terraform apply -var="flink_start_application=false"
set "RC=%ERRORLEVEL%"
popd
endlocal & exit /b %RC%
