@echo off
setlocal
set "REGION=%~1"
if "%REGION%"=="" set "REGION=ap-northeast-2"
pushd "%~dp0..\infra"
for /f "usebackq delims=" %%A in (`terraform output -raw flink_application_name`) do set "APP_NAME=%%A"
aws kinesisanalyticsv2 describe-application --region "%REGION%" --application-name "%APP_NAME%" --query "ApplicationDetail.{Name:ApplicationName,Status:ApplicationStatus,Runtime:RuntimeEnvironment}" --output table
set "RC=%ERRORLEVEL%"
popd
endlocal & exit /b %RC%
