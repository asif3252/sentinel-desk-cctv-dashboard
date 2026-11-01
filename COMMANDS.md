# Windows command reference

Run commands from the repository root unless stated otherwise. Never put NVR passwords into command lines, shared logs or issue reports; enter them through the dashboard.

## Obtain the project

```powershell
git clone https://github.com/asif3252/sentinel-desk-cctv-dashboard.git
cd sentinel-desk-cctv-dashboard
```

For ZIP downloads, extract the archive and open PowerShell in the folder containing `server.py`.

## Recommended launcher workflow

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-Detection.ps1
powershell -ExecutionPolicy Bypass -File .\Start.ps1
```

The first command installs inference dependencies. The second keeps the server in the current window. Open http://127.0.0.1:8765 in your browser. Press Ctrl+C in the server window to shut down. Restarting clears recorder credentials and in-memory events.

## Explicit Python 3.12 environment

```powershell
py --list
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe server.py
```

Replace `-3.12` with `-3.11` when appropriate. If an existing `.venv` uses an incompatible interpreter, stop the server and rename it as a backup before creating the new environment:

```powershell
Rename-Item -LiteralPath .venv -NewName .venv-backup
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Use a different backup name if `.venv-backup` already exists. Do not overwrite it.

## Verify installation

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip show opencv-python ultralytics
.\.venv\Scripts\python.exe -c "import cv2, ultralytics; print('Detection imports OK')"
```

Package discovery in the dashboard does not replace an import test. A broken binary dependency can be discoverable but fail to import.

## Verify code

```powershell
py -3 -m unittest discover -s . -p test_server.py
node --check web/app.js
```

Node.js is optional and only needed for the JavaScript syntax check. Backend tests do not download weights or connect to an NVR.

## Check the dashboard port

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen
```

If access is restricted or the cmdlet is unavailable, inspect the server startup message and close any older Sentinel Desk server window normally. Do not terminate unrelated processes.

## Update source and dependencies

```powershell
git status
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Commit or back up local source changes first. Stop the server before updating files; restart afterward. Requirements use version ranges and do not constitute a fully pinned reproducible environment. Record installed versions for a benchmark:

```powershell
.\.venv\Scripts\python.exe -m pip freeze
```

Review output before sharing it. This project does not require a public tunnel, router port-forwarding, firewall changes or administrator rights for normal loopback use.
