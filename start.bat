@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Multi-Agent Studio

echo ============================================
echo   Multi-Agent Studio — обновление и запуск
echo ============================================
echo.

where git >nul 2>&1
if %ERRORLEVEL%==0 (
  echo [1/3] Git pull...
  git pull origin main
  if errorlevel 1 (
    echo Внимание: git pull не удался. Продолжаем с локальной версией.
  ) else (
    echo OK: репозиторий обновлён.
  )
) else (
  echo [1/3] Git не найден — пропускаем обновление.
  echo Установите Git: https://git-scm.com/download/win
)

echo.
echo [2/3] Зависимости...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt

echo.
echo [3/3] Запуск Streamlit...
echo Браузер: http://localhost:8501
echo.
streamlit run app.py

pause
