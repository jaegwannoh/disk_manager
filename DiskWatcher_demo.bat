@echo off
rem DiskWatcher demo mode - fake servers, no SSH (uses demo_servers.txt)
start "" "C:\anaconda2\pythonw.exe" "%~dp0main.py" --demo
