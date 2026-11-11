@echo off
setlocal EnableExtensions
REM Russian console text is OEM code page 866.
REM Git stores this file as UTF-8 and checks it out as CP866 with CRLF.
REM Do not save it as UTF-8 and do not run chcp 65001.
REM The script copies itself to TEMP before git pull. cmd.exe keeps the
REM running batch open, and Git cannot replace that file on Windows.

if "%MAS_LAUNCHER%"=="1" goto work
set "MAS_LAUNCHER=1"
set "MAS_ROOT=%~dp0."
set "MAS_TMP=%TEMP%\mas-launcher-%RANDOM%%RANDOM%.bat"
copy /y "%~f0" "%MAS_TMP%" >nul
if errorlevel 1 goto work
"%MAS_TMP%" %*
set "RC=%ERRORLEVEL%"
del /q "%MAS_TMP%" >nul 2>&1
exit /b %RC%

:work
if defined MAS_ROOT goto cd_root
cd /d "%~dp0."
if errorlevel 1 goto cd_failed
goto dispatch
:cd_root
cd /d "%MAS_ROOT%"
if errorlevel 1 goto cd_failed

:dispatch
if /I "%~1"=="update" goto do_update
if /I "%~1"=="setup" goto do_setup

:do_run
call :update
if errorlevel 2 goto relaunch
call :deps
if errorlevel 1 goto failed
echo.
echo [3/3] Запуск Streamlit...
echo Браузер: http://localhost:8501
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
set "RC=%ERRORLEVEL%"
echo.
pause
exit /b %RC%

:do_update
call :update
if errorlevel 2 goto relaunch
exit /b 0

:do_setup
call :update
if errorlevel 2 goto relaunch
call :deps
if errorlevel 1 exit /b 1
exit /b 0

:relaunch
echo.
echo Файлы обновились. Перезапускаю start.bat...
set "MAS_LAUNCHER="
if not defined MAS_ROOT goto relaunch_self
"%MAS_ROOT%\start.bat" %*
set "RC=%ERRORLEVEL%"
exit /b %RC%
:relaunch_self
call "%~f0" %*
set "RC=%ERRORLEVEL%"
exit /b %RC%

:cd_failed
echo Не удалось открыть папку скрипта.
if /I "%~1"=="setup" exit /b 1
if /I "%~1"=="update" exit /b 1
pause
exit /b 1

:failed
echo.
echo Подготовка не удалась. Смотрите сообщения выше.
pause
exit /b 1

:update
set "GIT_TERMINAL_PROMPT=0"
set "GCM_INTERACTIVE=Never"
set "GIT_ASKPASS="
set "GIT_DIR="
set "GIT_WORK_TREE="
REM Command-line config, so a OneDrive "dubious ownership" check cannot
REM block pull. The asterisk is not passed on argv: cmd and Git for Windows
REM would otherwise expand it to local filenames.
set "GIT_CONFIG_COUNT=4"
set "GIT_CONFIG_KEY_0=safe.directory"
set "GIT_CONFIG_VALUE_0=*"
set "GIT_CONFIG_KEY_1=core.trustctime"
set "GIT_CONFIG_VALUE_1=false"
set "GIT_CONFIG_KEY_2=http.lowSpeedLimit"
set "GIT_CONFIG_VALUE_2=1"
set "GIT_CONFIG_KEY_3=http.lowSpeedTime"
set "GIT_CONFIG_VALUE_3=25"
call :find_git
if not defined GIT goto no_git
call :ensure_repo
if errorlevel 1 exit /b 0
call :repair_phantom
call :check_dirty
if errorlevel 1 exit /b 0
call :do_pull
if errorlevel 2 exit /b 2
exit /b 0

:no_git
echo [1/3] Git не найден. Обновление пропущено.
echo Искали в PATH и в Program Files\Git.
echo Установите Git: https://git-scm.com/download/win
echo В установщике отметьте Git from the command line and also from 3rd-party software.
echo Запускаю текущую версию.
exit /b 0

:find_git
set "GIT="
where git >nul 2>&1
if errorlevel 1 goto find_git_common
set "MAS_WHERE=%TEMP%\mas-where-git.txt"
where git > "%MAS_WHERE%" 2>nul
for /f "usebackq delims=" %%G in ("%MAS_WHERE%") do call :consider_git "%%G"
if defined GIT goto :eof
:find_git_common
if exist "%ProgramFiles%\Git\cmd\git.exe" set "GIT=%ProgramFiles%\Git\cmd\git.exe"
if defined GIT goto :eof
if exist "%ProgramFiles%\Git\bin\git.exe" set "GIT=%ProgramFiles%\Git\bin\git.exe"
if defined GIT goto :eof
if exist "%LocalAppData%\Programs\Git\cmd\git.exe" set "GIT=%LocalAppData%\Programs\Git\cmd\git.exe"
goto :eof

:consider_git
if defined GIT goto :eof
set "CAND=%~1"
set "PROBE=%CAND:\WindowsApps\=%"
if /I not "%CAND%"=="%PROBE%" goto :eof
set "GIT=%CAND%"
goto :eof

:ensure_repo
"%GIT%" rev-parse --is-inside-work-tree >nul 2>&1
if not errorlevel 1 exit /b 0
if exist ".git" goto bad_repo
echo [1/3] Это не git-репозиторий. Обновление пропущено.
echo Папка скачана архивом или скопирована без каталога .git.
echo git pull здесь не работает. Чтобы студия обновлялась, клонируйте ее:
echo   git clone https://github.com/Bot2217/Multi-Agent-Studio.git
echo   cd Multi-Agent-Studio
echo   start.bat
echo Сейчас запустится эта копия.
exit /b 1

:bad_repo
echo [1/3] Git не смог открыть репозиторий. Обновление пропущено.
echo Если папка в OneDrive, включите Всегда хранить на этом устройстве.
echo Если Git пишет про dubious ownership, выполните:
echo   git config --global --add safe.directory "%CD%"
echo Запускаю текущую версию.
exit /b 1

:repair_phantom
if not exist "start.bat" exit /b 0
set "MAS_LOG=%TEMP%\mas-git-log.txt"
del "%MAS_LOG%" >nul 2>&1
"%GIT%" hash-object --path=start.bat -- start.bat > "%MAS_LOG%" 2>nul
if errorlevel 1 exit /b 0
set "HWORK="
set /p HWORK=<"%MAS_LOG%"
del "%MAS_LOG%" >nul 2>&1
"%GIT%" rev-parse "HEAD:start.bat" > "%MAS_LOG%" 2>nul
if errorlevel 1 exit /b 0
set "HHEAD="
set /p HHEAD=<"%MAS_LOG%"
if not defined HWORK exit /b 0
if not defined HHEAD exit /b 0
if /I not "%HWORK%"=="%HHEAD%" exit /b 0
del "%MAS_LOG%" >nul 2>&1
"%GIT%" status --porcelain -- start.bat > "%MAS_LOG%" 2>nul
set "BATSTAT="
set /p BATSTAT=<"%MAS_LOG%"
if not defined BATSTAT exit /b 0
echo [1/3] start.bat числится измененным, но содержимое совпадает с Git.
echo Восстанавливаю файл, чтобы кодировка CP866 не блокировала обновление.
"%GIT%" checkout -f -- start.bat >nul 2>&1
exit /b 0

:check_dirty
"%GIT%" update-index --refresh >nul 2>&1
"%GIT%" diff --quiet
if errorlevel 1 goto dirty_tree
"%GIT%" diff --cached --quiet
if errorlevel 1 goto dirty_tree
exit /b 0

:dirty_tree
echo [1/3] Обновление пропущено: есть локальные изменения.
echo git pull --ff-only не затирает их.
echo Уберите или закоммитьте правки и запустите снова.
echo Продолжаю с текущей версией.
exit /b 1

:do_pull
set "MAS_LOG=%TEMP%\mas-git-log.txt"
del "%MAS_LOG%" >nul 2>&1
"%GIT%" rev-parse HEAD > "%MAS_LOG%" 2>nul
set "OLDREV="
set /p OLDREV=<"%MAS_LOG%"
echo [1/3] git pull --ff-only origin main
del "%MAS_LOG%" >nul 2>&1
"%GIT%" fetch origin main > "%MAS_LOG%" 2>&1
set "FETCHRC=%ERRORLEVEL%"
type "%MAS_LOG%"
if not "%FETCHRC%"=="0" goto network_fail
"%GIT%" merge-base --is-ancestor HEAD FETCH_HEAD >nul 2>&1
if not errorlevel 1 goto can_ff
"%GIT%" merge-base --is-ancestor FETCH_HEAD HEAD >nul 2>&1
if not errorlevel 1 goto say_current
goto ff_fail
:can_ff
"%GIT%" diff --quiet
if errorlevel 1 goto dirty_tree
"%GIT%" diff --cached --quiet
if errorlevel 1 goto dirty_tree
del "%MAS_LOG%" >nul 2>&1
"%GIT%" pull --ff-only --no-rebase origin main > "%MAS_LOG%" 2>&1
set "PULLRC=%ERRORLEVEL%"
type "%MAS_LOG%"
if not "%PULLRC%"=="0" goto ff_fail
goto pull_ok
:network_fail
echo [1/3] Не удалось связаться с origin и получить ветку main.
echo Проверьте интернет. Remote origin должен указывать на репозиторий.
echo Продолжаю с текущей версией.
exit /b 0

:ff_fail
echo [1/3] Не удалось обновить без слияния: нет fast-forward.
echo Ветка разошлась с origin/main, это другая ветка или detached HEAD.
echo Продолжаю с текущей версией.
echo Вручную: git checkout main
echo         git pull --ff-only origin main
exit /b 0

:pull_ok
del "%MAS_LOG%" >nul 2>&1
"%GIT%" rev-parse HEAD > "%MAS_LOG%" 2>nul
set "NEWREV="
set /p NEWREV=<"%MAS_LOG%"
if not defined OLDREV goto say_current
if not defined NEWREV goto say_current
if /I "%OLDREV%"=="%NEWREV%" goto say_current
echo [1/3] Репозиторий обновлен.
exit /b 2

:say_current
echo [1/3] Уже последняя версия.
exit /b 0

:deps
echo.
echo [2/3] Зависимости...
set "PY="
where python >nul 2>&1
if errorlevel 1 goto try_py_launcher
set "PY=python"
goto have_py
:try_py_launcher
where py >nul 2>&1
if errorlevel 1 goto no_python
set "PY=py -3"
:have_py
if exist ".venv\Scripts\python.exe" goto pip_install
%PY% -m venv .venv
if errorlevel 1 goto venv_fail
:pip_install
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto pip_fail
exit /b 0
:no_python
echo Не найден Python 3. Установите Python и добавьте команду python или py в PATH.
exit /b 1
:venv_fail
echo Не удалось создать виртуальное окружение.
exit /b 1
:pip_fail
echo Не удалось установить зависимости.
exit /b 1
