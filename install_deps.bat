@echo off
REM Batch script to install Python dependencies for the College Marketplace project.


echo Ensuring pip is up-to-date...
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

REM Check if installation was successful
if %ERRORLEVEL% neq 0 (
    echo.
    echo *******************************************
    echo *   ERROR: Installation failed.           *
    echo *   Please check the messages above.      *
    echo *******************************************
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully.
echo You can now run the application (e.g., using 'flask run').
pause