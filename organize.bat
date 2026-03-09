@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ================================================================
echo  DRY-RUN - Apercu des modifications
echo ================================================================
echo.
python "C:\Users\pierr\Code\Scripts\Powershell\organize-films\organize_films.py" "%~dp0" --dry-run

echo.
choice /M "Appliquer les modifications ?"
if errorlevel 2 goto end
if errorlevel 1 (
    echo.
    python "C:\Users\pierr\Code\Scripts\Powershell\organize-films\organize_films.py" "%~dp0" --run-force
)

:end
echo.
pause
