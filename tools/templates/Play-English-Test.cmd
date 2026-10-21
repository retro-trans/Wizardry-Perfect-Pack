@echo off
setlocal
for %%I in ("%~dp0..\..") do set "WIZARDRY_TEST_ROOT=%%~fI"
set "WIZARDRY_TEST_RUNTIME=%WIZARDRY_TEST_ROOT%\work\source\rpcs3_reader"
set "WIZARDRY_TEST_GAME=%WIZARDRY_TEST_RUNTIME%\dev_hdd0\game\NPJB00162\USRDIR\EBOOT.elf"
set "WIZARDRY_TEST_PYTHON=%WIZARDRY_TEST_ROOT%\work\local\venv\Scripts\python.exe"
if not exist "%WIZARDRY_TEST_PYTHON%" set "WIZARDRY_TEST_PYTHON=C:\Users\Binh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%WIZARDRY_TEST_RUNTIME%\rpcs3.exe" (
  echo The project-local test emulator is missing.
  pause
  exit /b 1
)
powershell -NoProfile -NonInteractive -Command "$target = [IO.Path]::GetFullPath($env:WIZARDRY_TEST_RUNTIME + '\rpcs3.exe'); $active = Get-Process rpcs3 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $target }; if ($active) { Write-Host 'Save your progress and close this project''s test emulator before starting the updated game.'; exit 2 }; exit 0"
if errorlevel 1 (
  pause
  exit /b 1
)
if "%~1"=="--check" (
  echo Launcher preflight passed.
  exit /b 0
)
pushd "%WIZARDRY_TEST_ROOT%"
"%WIZARDRY_TEST_PYTHON%" "tools\stage_test.py" "work\output\0.1.23" --changed-files --write
if errorlevel 1 (
  popd
  echo The update could not be applied. The test game has not been started.
  pause
  exit /b 1
)
popd
start "" /D "%WIZARDRY_TEST_RUNTIME%" "%WIZARDRY_TEST_RUNTIME%\rpcs3.exe" "%WIZARDRY_TEST_GAME%"
