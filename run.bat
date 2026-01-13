# GammaOption - Quick Start Scripts

@echo off
echo ========================================
echo GammaOption - SPX Gamma Analysis
echo ========================================
echo.

:menu
echo Select an option:
echo.
echo 1. Run Full Analysis
echo 2. Quick Update (prices + alerts)
echo 3. Start Scheduler (automated)
echo 4. Open Dashboard
echo 5. Install Dependencies
echo 6. Setup Environment
echo 7. Exit
echo.

set /p choice="Enter choice (1-7): "

if "%choice%"=="1" goto analyze
if "%choice%"=="2" goto update
if "%choice%"=="3" goto schedule
if "%choice%"=="4" goto dashboard
if "%choice%"=="5" goto install
if "%choice%"=="6" goto setup
if "%choice%"=="7" goto end

echo Invalid choice. Please try again.
echo.
goto menu

:analyze
echo.
echo Running full analysis...
python main.py analyze
pause
goto menu

:update
echo.
echo Running quick update...
python main.py update
pause
goto menu

:schedule
echo.
echo Starting scheduler (automated mode)...
echo Press Ctrl+C to stop
python main.py schedule
pause
goto menu

:dashboard
echo.
echo Opening dashboard...
echo Dashboard will open in your browser at http://localhost:8501
python main.py dashboard
pause
goto menu

:install
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Installation complete!
pause
goto menu

:setup
echo.
echo Setting up environment...
if not exist .env (
    copy .env.example .env
    echo .env file created. Please edit it with your API keys.
    notepad .env
) else (
    echo .env file already exists.
)
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    echo Virtual environment created. Activate it with: venv\Scripts\activate.ps1
)
echo.
echo Setup complete!
pause
goto menu

:end
echo.
echo Goodbye!
exit /b
