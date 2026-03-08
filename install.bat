@echo off
REM Installation script for Meshcore Firmware Editor and Flasher (Windows)

echo ==========================================
echo Meshcore Firmware Editor and Flasher - Installation
echo ==========================================
echo.

REM Check Python
echo Checking Python installation...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo [OK] Python found: %PYTHON_VERSION%
    set PYTHON_CMD=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        for /f "tokens=2" %%i in ('py --version 2^>^&1') do set PYTHON_VERSION=%%i
        echo [OK] Python found: %PYTHON_VERSION%
        set PYTHON_CMD=py
    ) else (
        python3 --version >nul 2>&1
        if %errorlevel% equ 0 (
            for /f "tokens=2" %%i in ('python3 --version 2^>^&1') do set PYTHON_VERSION=%%i
            echo [OK] Python found: %PYTHON_VERSION%
            set PYTHON_CMD=python3
        ) else (
            echo [ERROR] Python not found!
            echo Please install Python 3.6 or higher from https://www.python.org/downloads/
            echo Make sure to check "Add Python to PATH" during installation.
            pause
            exit /b 1
        )
    )
)

REM Check pip
echo.
echo Checking pip installation...
%PYTHON_CMD% -m pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] pip found
    set PIP_CMD=%PYTHON_CMD% -m pip
) else (
    echo [WARNING] pip not found, attempting to install...
    %PYTHON_CMD% -m ensurepip --upgrade
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install pip. Please install pip manually.
        pause
        exit /b 1
    )
    set PIP_CMD=%PYTHON_CMD% -m pip
)

REM Check Tkinter
echo.
echo Checking Tkinter...
%PYTHON_CMD% -c "import tkinter" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Tkinter is available
) else (
    echo [WARNING] Tkinter not found
    echo Tkinter should be included with Python. Try reinstalling Python.
)

REM Install the package
echo.
echo Installing Meshcore Firmware Editor and Flasher...
%PIP_CMD% install -e . --user

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo Installation completed successfully!
    echo ==========================================
    echo.
    echo You can now run the application with:
    echo   meshcore-firmware-editor
    echo.
    echo Or directly with:
    echo   %PYTHON_CMD% meshcore_flasher.py
    echo.
) else (
    echo [ERROR] Installation failed!
    pause
    exit /b 1
)

REM Install optional dependencies
echo.
echo Installing optional dependencies...
echo.

REM Install PlatformIO
echo Installing PlatformIO...
pio --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=1,2" %%i in ('pio --version 2^>^&1') do (
        echo [OK] PlatformIO already installed: %%i %%j
        goto :pio_done
    )
    :pio_done
) else (
    echo Installing PlatformIO via pip...
    %PIP_CMD% install platformio --user
    if %errorlevel% equ 0 (
        echo [OK] PlatformIO installed successfully
        echo Note: You may need to restart your terminal for 'pio' command to be available
    ) else (
        echo [WARNING] Failed to install PlatformIO. You can install it manually:
        echo   %PIP_CMD% install platformio
    )
)

REM Install Git
echo.
echo Installing Git...
git --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=1,2,3" %%i in ('git --version 2^>^&1') do (
        echo [OK] Git already installed: %%i %%j %%k
        goto :git_done
    )
    :git_done
) else (
    echo Installing Git...
    REM Try winget first (Windows 10+)
    where winget >nul 2>&1
    if %errorlevel% equ 0 (
        echo Using winget to install Git...
        winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
        if %errorlevel% equ 0 (
            echo [OK] Git installed via winget
            echo Note: You may need to restart your terminal for 'git' command to be available
        ) else (
            echo [WARNING] winget installation failed, trying chocolatey...
            REM Try chocolatey
            where choco >nul 2>&1
            if %errorlevel% equ 0 (
                choco install git -y
                if %errorlevel% equ 0 (
                    echo [OK] Git installed via chocolatey
                ) else (
                    echo [WARNING] chocolatey installation failed
                    goto :git_manual
                )
            ) else (
                goto :git_manual
            )
        )
    ) else (
        REM Try chocolatey
        where choco >nul 2>&1
        if %errorlevel% equ 0 (
            choco install git -y
            if %errorlevel% equ 0 (
                echo [OK] Git installed via chocolatey
            ) else (
                goto :git_manual
            )
        ) else (
            :git_manual
            echo [WARNING] Could not auto-install Git
            echo   Please install Git manually from: https://git-scm.com/download/win
            echo   Or install a package manager (winget or chocolatey) and run this script again
        )
    )
)

echo.
echo ==========================================
echo Installation completed!
echo ==========================================
echo.
echo You can now run the application with:
echo   meshcore-firmware-editor
echo.
echo Or directly with:
echo   %PYTHON_CMD% meshcore_flasher.py
echo.
pause

