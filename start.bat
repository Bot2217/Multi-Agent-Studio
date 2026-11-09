@echo off
setlocal EnableExtensions
REM Russian console messages are OEM code page 866.
REM Git checks this file out as CP866 with CRLF. Do not save it as UTF-8
REM and do not run chcp 65001: cmd.exe then splits commands into fragments.
cd /d "%~dp0" || exit /b 1

if /I "%~1"=="setup" goto setup

call :setup
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

:failed
echo.
echo Подготовка не удалась. Смотрите сообщения выше.
pause
exit /b 1

:setup
set "GIT_TERMINAL_PROMPT=0"
where git >nul 2>&1
if %ERRORLEVEL%==0 (
  echo [1/3] Git pull...
  git pull origin main
  if errorlevel 1 (
    echo Внимание: git pull не удался. Продолжаем с локальной версией.
  ) else (
    echo OK: репозиторий обновлен.
  )
) else (
  echo [1/3] Git не найден - пропускаем обновление.
  echo Установите Git: https://git-scm.com/download/win
)

echo.
echo [2/3] Зависимости...
set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY (
  where py >nul 2>&1 && set "PY=py -3"
)
if not defined PY (
  echo Не найден Python 3. Установите Python и добавьте команду python или py в PATH.
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Не удалось создать виртуальное окружение.
    exit /b 1
  )
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Не удалось установить зависимости.
  exit /b 1
)
exit /b 0
