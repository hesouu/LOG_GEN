@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul

rem ============================================================
rem Run one-off Fargate synthetic log generator
rem Usage:
rem   run-generator.bat [DOMAIN] [DURATION_SECONDS] [BASE_RPS] [CORRUPTION_RATE] [TASK_COUNT] [REGION] [TIME_SCALE]
rem ============================================================

set "DOMAIN=%~1"
if not defined DOMAIN set "DOMAIN=ecommerce"
set "DURATION_SECONDS=%~2"
if not defined DURATION_SECONDS set "DURATION_SECONDS=300"
set "BASE_RPS=%~3"
if not defined BASE_RPS set "BASE_RPS=2.0"
set "CORRUPTION_RATE=%~4"
if not defined CORRUPTION_RATE set "CORRUPTION_RATE=0.03"
set "TASK_COUNT=%~5"
if not defined TASK_COUNT set "TASK_COUNT=1"
set "REGION=%~6"
if not defined REGION set "REGION=ap-northeast-2"
set "TIME_SCALE=%~7"
if not defined TIME_SCALE set "TIME_SCALE=1.0"

call :validate_domain
if errorlevel 1 exit /b 1
call :require_cmd aws
if errorlevel 1 exit /b 1
call :require_cmd terraform
if errorlevel 1 exit /b 1

for %%I in ("%~dp0..") do set "ROOT=%%~fI"
set "INFRA=%ROOT%\infra"
set "RUN_ID=loggen-%RANDOM%%RANDOM%-%RANDOM%"

call :tf_output_raw ecs_cluster_name CLUSTER
if errorlevel 1 (
  echo [ERROR] ecs_cluster_name not found.
  exit /b 1
)

call :tf_output_raw ecs_task_definition_arn TASK_DEFINITION
if errorlevel 1 (
  echo [ERROR] ecs_task_definition_arn not found.
  exit /b 1
)

call :tf_output_raw security_group_id SECURITY_GROUP
if errorlevel 1 (
  echo [ERROR] security_group_id not found.
  exit /b 1
)

call :tf_output_json public_subnet_ids SUBNETS_JSON
if errorlevel 1 (
  echo [ERROR] public_subnet_ids not found.
  exit /b 1
)

setlocal EnableDelayedExpansion
set "SUBNET_CSV=!SUBNETS_JSON:[=!"
set "SUBNET_CSV=!SUBNET_CSV:]=!"
set "SUBNET_CSV=!SUBNET_CSV:\"=!"
set "SUBNET_CSV=!SUBNET_CSV: =!"
for /f "delims=" %%A in ("!SUBNET_CSV!") do endlocal & set "SUBNET_CSV=%%~A"

set "OVERRIDE_FILE=%TEMP%\loggen-overrides-%RUN_ID%.json"
> "%OVERRIDE_FILE%" echo {
>>"%OVERRIDE_FILE%" echo   "containerOverrides": [
>>"%OVERRIDE_FILE%" echo     {
>>"%OVERRIDE_FILE%" echo       "name": "log-generator",
>>"%OVERRIDE_FILE%" echo       "environment": [
>>"%OVERRIDE_FILE%" echo         {"name":"DOMAIN","value":"%DOMAIN%"},
>>"%OVERRIDE_FILE%" echo         {"name":"DURATION_SECONDS","value":"%DURATION_SECONDS%"},
>>"%OVERRIDE_FILE%" echo         {"name":"BASE_RPS","value":"%BASE_RPS%"},
>>"%OVERRIDE_FILE%" echo         {"name":"TIME_SCALE","value":"%TIME_SCALE%"},
>>"%OVERRIDE_FILE%" echo         {"name":"CORRUPTION_RATE","value":"%CORRUPTION_RATE%"},
>>"%OVERRIDE_FILE%" echo         {"name":"INCLUDE_CORRUPTION_LABEL","value":"false"},
>>"%OVERRIDE_FILE%" echo         {"name":"OUTPUT_MODE","value":"stdout"},
>>"%OVERRIDE_FILE%" echo         {"name":"RUN_ID","value":"%RUN_ID%"}
>>"%OVERRIDE_FILE%" echo       ]
>>"%OVERRIDE_FILE%" echo     }
>>"%OVERRIDE_FILE%" echo   ]
>>"%OVERRIDE_FILE%" echo }

echo.
echo ============================================================
echo Fargate synthetic log generator
echo ============================================================
echo Run ID          : %RUN_ID%
echo Domain          : %DOMAIN%
echo Duration        : %DURATION_SECONDS%s
echo Base RPS        : %BASE_RPS%
echo Time scale      : %TIME_SCALE%
echo Corruption rate : %CORRUPTION_RATE%
echo Tasks           : %TASK_COUNT%
echo Region          : %REGION%
echo Cluster         : %CLUSTER%
echo.

aws ecs run-task ^
  --region "%REGION%" ^
  --cluster "%CLUSTER%" ^
  --launch-type FARGATE ^
  --task-definition "%TASK_DEFINITION%" ^
  --count "%TASK_COUNT%" ^
  --started-by "%RUN_ID%" ^
  --network-configuration "awsvpcConfiguration={subnets=[%SUBNET_CSV%],securityGroups=[%SECURITY_GROUP%],assignPublicIp=ENABLED}" ^
  --overrides "file://%OVERRIDE_FILE%" ^
  --query "tasks[].taskArn" ^
  --output table

set "RUN_RC=%ERRORLEVEL%"
del /q "%OVERRIDE_FILE%" >nul 2>&1
if not "%RUN_RC%"=="0" exit /b %RUN_RC%

call :tf_output_raw cloudwatch_log_group LOG_GROUP
if errorlevel 1 set "LOG_GROUP=/ecs/de-ai-09-loggen"

echo.
echo Task started.
echo Follow generated logs:
echo   aws logs tail "%LOG_GROUP%" --follow --region "%REGION%"
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

:tf_output_json
set "TF_OUTPUT_NAME=%~1"
set "TF_OUTPUT_FILE=%TEMP%\loggen-tf-%RANDOM%-%RANDOM%.json"
terraform -chdir="%INFRA%" output -json "%TF_OUTPUT_NAME%" > "%TF_OUTPUT_FILE%" 2>nul
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

:validate_domain
if /I "%DOMAIN%"=="ecommerce" exit /b 0
if /I "%DOMAIN%"=="finance" exit /b 0
if /I "%DOMAIN%"=="smartfactory" exit /b 0
if /I "%DOMAIN%"=="game" exit /b 0
echo [ERROR] DOMAIN must be ecommerce, finance, smartfactory, or game.
exit /b 1

:require_cmd
where %~1 >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Command not found: %~1
  exit /b 1
)
exit /b 0
