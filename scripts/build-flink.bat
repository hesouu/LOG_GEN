@echo off
setlocal

set "ROOT=%~dp0.."
set "FLINK_DIR=%ROOT%\flink"

where mvn >nul 2>nul
if errorlevel 1 (
  echo ERROR: Maven(mvn)이 필요합니다. JDK 11 + Maven을 설치한 뒤 다시 실행하세요.
  exit /b 1
)

echo [1/2] Build PyFlink application package
pushd "%FLINK_DIR%"
call mvn clean package
if errorlevel 1 (
  popd
  exit /b 1
)
popd

if not exist "%FLINK_DIR%\target\flink-silver.zip" (
  echo ERROR: Flink 배포 ZIP이 생성되지 않았습니다.
  exit /b 1
)

echo [2/2] Build complete
echo %FLINK_DIR%\target\flink-silver.zip

endlocal
