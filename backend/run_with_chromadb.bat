@echo off
REM Run backend using the same Python that has chromadb (e.g. Anaconda).
REM Use this if your venv shows "No module named 'chromadb'" and pip install fails due to file lock.
cd /d "%~dp0"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
