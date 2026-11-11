@echo off
setlocal EnableExtensions
cd /d "%~dp0.."
set "ROOT=%CD%"
echo UPDATE_PROBE git %ROOT%
git --version
set "SANDBOX=%TEMP%\mas-update-%RANDOM%%RANDOM%"
mkdir "%SANDBOX%"
if errorlevel 1 goto fail

cd /d "%ROOT%"
git status --porcelain -- start.bat > "%SANDBOX%\bat.txt"
if errorlevel 1 goto fail_bat
for %%A in ("%SANDBOX%\bat.txt") do if not %%~zA==0 goto fail_bat

set "UP=%SANDBOX%\upstream.git"
set "SEED=%SANDBOX%\seed"
set "WT=%SANDBOX%\wt"
set "WT2=%SANDBOX%\wt2"
git init --bare "%UP%"
if errorlevel 1 goto fail
git init -b main "%SEED%"
if errorlevel 1 goto fail
git -C "%SEED%" config user.email ci@example.com
git -C "%SEED%" config user.name CI
git -C "%SEED%" config core.autocrlf true
git -C "%SEED%" config core.safecrlf false
copy /y "%ROOT%\.gitattributes" "%SEED%\.gitattributes" >nul
if errorlevel 1 goto fail
copy /y "%ROOT%\start.bat" "%SEED%\start.bat" >nul
if errorlevel 1 goto fail
git -C "%SEED%" add -- .gitattributes start.bat
if errorlevel 1 goto fail
git -C "%SEED%" commit -m base
if errorlevel 1 goto fail
git -C "%SEED%" remote add origin "%UP%"
git -C "%UP%" symbolic-ref HEAD refs/heads/main
git -C "%SEED%" push origin main
if errorlevel 1 goto fail

git clone -b main "%UP%" "%WT%"
if errorlevel 1 goto fail
git -C "%WT%" config user.email ci@example.com
git -C "%WT%" config user.name CI
git -C "%WT%" config core.autocrlf true
git -C "%WT%" config core.safecrlf false
git clone -b main "%UP%" "%WT2%"
if errorlevel 1 goto fail
git -C "%WT2%" config user.email ci@example.com
git -C "%WT2%" config user.name CI
git -C "%WT2%" config core.autocrlf true
git -C "%WT2%" config core.safecrlf false

echo rem extra>> "%WT2%\notes.txt"
echo REM probe-marker>> "%WT2%\start.bat"
git -C "%WT2%" add -- notes.txt start.bat
if errorlevel 1 goto fail
git -C "%WT2%" commit -m ahead
if errorlevel 1 goto fail
git -C "%WT2%" push origin main
if errorlevel 1 goto fail

cd /d "%WT%"
git status --porcelain > "%SANDBOX%\pre.txt"
if errorlevel 1 goto fail_preclean
for %%A in ("%SANDBOX%\pre.txt") do if not %%~zA==0 goto fail_preclean
git branch --unset-upstream
if errorlevel 1 goto fail
git rev-parse HEAD > "%SANDBOX%\old.txt"
set /p OLD=<"%SANDBOX%\old.txt"
call start.bat update
if errorlevel 1 goto fail
git rev-parse HEAD > "%SANDBOX%\new.txt"
set /p NEW=<"%SANDBOX%\new.txt"
if "%OLD%"=="%NEW%" goto fail_nff
if not exist notes.txt goto fail_notes
findstr /c:"probe-marker" start.bat >nul
if errorlevel 1 goto fail_marker
git rev-parse origin/main > "%SANDBOX%\om.txt"
set /p OM=<"%SANDBOX%\om.txt"
if not "%NEW%"=="%OM%" goto fail_nff

echo rem more>> "%WT2%\notes.txt"
git -C "%WT2%" add -- notes.txt
if errorlevel 1 goto fail
git -C "%WT2%" commit -m more
if errorlevel 1 goto fail
git -C "%WT2%" push origin main
if errorlevel 1 goto fail
cd /d "%WT%"
git checkout --detach HEAD
if errorlevel 1 goto fail
git rev-parse HEAD > "%SANDBOX%\old.txt"
set /p OLD=<"%SANDBOX%\old.txt"
call start.bat update
if errorlevel 1 goto fail_detach
git rev-parse HEAD > "%SANDBOX%\new.txt"
set /p NEW=<"%SANDBOX%\new.txt"
if "%OLD%"=="%NEW%" goto fail_detach
git rev-parse origin/main > "%SANDBOX%\om.txt"
set /p OM=<"%SANDBOX%\om.txt"
if not "%NEW%"=="%OM%" goto fail_detach

echo dirty>> "%WT%\notes.txt"
git -C "%WT%" rev-parse HEAD > "%SANDBOX%\old.txt"
set /p OLD=<"%SANDBOX%\old.txt"
echo rem blocked>> "%WT2%\notes.txt"
git -C "%WT2%" add -- notes.txt
if errorlevel 1 goto fail
git -C "%WT2%" commit -m blocked
if errorlevel 1 goto fail
git -C "%WT2%" push origin main
if errorlevel 1 goto fail
cd /d "%WT%"
call start.bat update
if errorlevel 1 goto fail_dirty
git rev-parse HEAD > "%SANDBOX%\new.txt"
set /p NEW=<"%SANDBOX%\new.txt"
if not "%OLD%"=="%NEW%" goto fail_dirty
findstr /c:"dirty" notes.txt >nul
if errorlevel 1 goto fail_dirty

git remote set-url origin https://127.0.0.1:9/no.git
call start.bat update
if errorlevel 1 goto fail_net
git rev-parse HEAD > "%SANDBOX%\new.txt"
set /p NEW=<"%SANDBOX%\new.txt"
if not "%OLD%"=="%NEW%" goto fail_net

set "ZIP=%SANDBOX%\zip"
mkdir "%ZIP%"
copy /y "%ROOT%\start.bat" "%ZIP%\start.bat" >nul
if errorlevel 1 goto fail_zip
cd /d "%ZIP%"
call start.bat update
if errorlevel 1 goto fail_zip

echo UPDATE_PROBE_OK
exit /b 0

:fail_preclean
echo FAIL sandbox clone has local changes before pull
type "%SANDBOX%\pre.txt"
git -C "%WT%" diff
goto fail
:fail_nff
echo FAIL fast-forward did not move HEAD to origin/main
git -C "%WT%" status
git -C "%WT%" log --oneline -5
goto fail
:fail_notes
echo FAIL notes.txt missing after fast-forward
goto fail
:fail_marker
echo FAIL start.bat was not updated while the launcher was running
goto fail
:fail_detach
echo FAIL detached HEAD did not fast-forward
git -C "%WT%" status
git -C "%WT%" log --oneline -5
goto fail
:fail_dirty
echo FAIL local changes were overwritten or update returned an error
goto fail
:fail_net
echo FAIL bad origin changed HEAD or failed the process
goto fail
:fail_zip
echo FAIL zip copy update returned an error
goto fail
:fail_bat
echo FAIL start.bat looks modified after checkout
type "%SANDBOX%\bat.txt"
git -C "%ROOT%" diff -- start.bat
goto fail
:fail
echo UPDATE_PROBE_FAILED
exit /b 1
