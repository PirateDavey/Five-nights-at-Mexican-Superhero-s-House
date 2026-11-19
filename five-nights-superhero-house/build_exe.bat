@echo off
REM Builds dist\SuperheroHouse.exe on Windows (needs Python 3.10+ from python.org)
py -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :fail
py main.py --smoke
if errorlevel 1 goto :fail
py -m PyInstaller --noconsole --onefile --name SuperheroHouse main.py
if errorlevel 1 goto :fail
echo.
echo Done! Your game is at dist\SuperheroHouse.exe
goto :eof
:fail
echo Build failed.
exit /b 1
