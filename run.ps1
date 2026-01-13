# GammaOption - PowerShell Quick Start Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "GammaOption - SPX Gamma Analysis" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

function Show-Menu {
    Write-Host "Select an option:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Run Full Analysis"
    Write-Host "2. Quick Update (prices + alerts)"
    Write-Host "3. Start Scheduler (automated)"
    Write-Host "4. Open Dashboard"
    Write-Host "5. Install Dependencies"
    Write-Host "6. Setup Environment"
    Write-Host "7. View Logs"
    Write-Host "8. Exit"
    Write-Host ""
}

function Run-Analysis {
    Write-Host "`nRunning full analysis..." -ForegroundColor Green
    python main.py analyze
    Write-Host "`nPress any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

function Run-Update {
    Write-Host "`nRunning quick update..." -ForegroundColor Green
    python main.py update
    Write-Host "`nPress any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

function Run-Scheduler {
    Write-Host "`nStarting scheduler (automated mode)..." -ForegroundColor Green
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
    python main.py schedule
}

function Run-Dashboard {
    Write-Host "`nOpening dashboard..." -ForegroundColor Green
    Write-Host "Dashboard will open in your browser at http://localhost:8501" -ForegroundColor Cyan
    python main.py dashboard
}

function Install-Dependencies {
    Write-Host "`nInstalling dependencies..." -ForegroundColor Green
    pip install -r requirements.txt
    Write-Host "`nInstallation complete!" -ForegroundColor Green
    Write-Host "`nPress any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

function Setup-Environment {
    Write-Host "`nSetting up environment..." -ForegroundColor Green
    
    # Create .env if it doesn't exist
    if (-not (Test-Path .env)) {
        Copy-Item .env.example .env
        Write-Host ".env file created. Please edit it with your API keys." -ForegroundColor Yellow
        notepad .env
    } else {
        Write-Host ".env file already exists." -ForegroundColor Cyan
    }
    
    # Create venv if it doesn't exist
    if (-not (Test-Path venv)) {
        Write-Host "Creating virtual environment..." -ForegroundColor Yellow
        python -m venv venv
        Write-Host "Virtual environment created." -ForegroundColor Green
        Write-Host "Activate it with: .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    }
    
    # Create directories
    New-Item -ItemType Directory -Force -Path data | Out-Null
    New-Item -ItemType Directory -Force -Path logs | Out-Null
    
    Write-Host "`nSetup complete!" -ForegroundColor Green
    Write-Host "`nPress any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

function View-Logs {
    Write-Host "`nRecent log files:" -ForegroundColor Green
    Get-ChildItem logs -Filter *.log | Sort-Object LastWriteTime -Descending | Select-Object -First 5 | Format-Table Name, LastWriteTime, Length
    
    Write-Host "`nWhich log would you like to view?"
    Write-Host "1. Latest application log"
    Write-Host "2. Latest scheduler log"
    Write-Host "3. Alerts log"
    Write-Host "4. Return to main menu"
    
    $logChoice = Read-Host "`nEnter choice (1-4)"
    
    switch ($logChoice) {
        "1" {
            $latestLog = Get-ChildItem logs -Filter app_*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($latestLog) {
                Get-Content $latestLog.FullName -Tail 50
            }
        }
        "2" {
            $latestLog = Get-ChildItem logs -Filter scheduler_*.log | Sort-Object LastWriteTime -Descending | Select-Object -First 1
            if ($latestLog) {
                Get-Content $latestLog.FullName -Tail 50
            }
        }
        "3" {
            if (Test-Path logs\alerts.jsonl) {
                Get-Content logs\alerts.jsonl -Tail 20
            } else {
                Write-Host "No alerts log found." -ForegroundColor Yellow
            }
        }
    }
    
    Write-Host "`nPress any key to continue..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

# Main loop
do {
    Clear-Host
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "GammaOption - SPX Gamma Analysis" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    Show-Menu
    $choice = Read-Host "Enter choice (1-8)"
    
    switch ($choice) {
        "1" { Run-Analysis }
        "2" { Run-Update }
        "3" { Run-Scheduler }
        "4" { Run-Dashboard }
        "5" { Install-Dependencies }
        "6" { Setup-Environment }
        "7" { View-Logs }
        "8" { 
            Write-Host "`nGoodbye!" -ForegroundColor Cyan
            exit 
        }
        default { 
            Write-Host "`nInvalid choice. Please try again." -ForegroundColor Red
            Start-Sleep -Seconds 2
        }
    }
} while ($true)
