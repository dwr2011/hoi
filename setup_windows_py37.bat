@echo off
echo [1/4] Using Python launcher...
py -3.7 --version || goto :err

echo [2/4] Upgrading pip/setuptools/wheel...
py -3.7 -m pip install --upgrade pip setuptools wheel || goto :err

echo [3/4] Installing Python 3.7 compatible dependencies...
py -3.7 -m pip install -r requirements-py37.txt || goto :err

echo [4/4] Starting server on http://127.0.0.1:9000 ...
py -3.7 server.py --host 127.0.0.1 --port 9000 || goto :err

goto :eof
:err
echo Setup failed. Please copy the full output and send it.
exit /b 1
