@echo off
setlocal
echo ================================================================
echo  Hecos — Llama.cpp Binary Installer
echo ================================================================
echo.
echo This script downloads the standalone llama-server.exe binary
echo from the official llama.cpp GitHub releases.
echo.
echo Ollama does NOT need to be installed or running.
echo Hecos manages the llama-server process completely on its own.
echo.

:: Detect Hecos root (script is in scripts\, go up one level)
set "HECOS_ROOT=%~dp0.."
set "BIN_DIR=%HECOS_ROOT%\bin"

echo [INFO] Hecos root: %HECOS_ROOT%
echo [INFO] Binary destination: %BIN_DIR%
echo.

:: Detect Python executable
if exist "%HECOS_ROOT%\python_env\Scripts\python.exe" (
    echo [INFO] Detected Hecos python_env.
    set "PYTHON_EXE=%HECOS_ROOT%\python_env\Scripts\python.exe"
) else if exist "%HECOS_ROOT%\venv\Scripts\python.exe" (
    echo [INFO] Detected Hecos venv.
    set "PYTHON_EXE=%HECOS_ROOT%\venv\Scripts\python.exe"
) else (
    echo [INFO] No venv detected. Using system Python.
    set "PYTHON_EXE=python"
)

echo [INFO] Using Python: %PYTHON_EXE%
echo.

:: Use Python to download the zip and extract llama-server.exe
echo [INFO] Downloading llama.cpp release (CUDA 12.4 build)...
echo        This may take a few minutes depending on your connection.
echo.

"%PYTHON_EXE%" -c "
import urllib.request, zipfile, io, os, sys

bin_dir = r'%BIN_DIR%'
os.makedirs(bin_dir, exist_ok=True)

# Try CUDA 12.4 build first, then CPU-only fallback
sources = [
    ('https://github.com/ggml-org/llama.cpp/releases/download/b5540/llama-b5540-bin-win-cuda-cu12.4-x64.zip', 'CUDA 12.4'),
    ('https://github.com/ggml-org/llama.cpp/releases/download/b5540/llama-b5540-bin-win-avx2-x64.zip', 'CPU-only AVX2'),
]

for url, label in sources:
    try:
        print(f'  Trying {label} build: {url}')
        with urllib.request.urlopen(url, timeout=180) as r:
            data = r.read()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            extracted = []
            for member in z.namelist():
                basename = os.path.basename(member)
                if not basename:
                    continue
                if basename.endswith('.exe') or basename.endswith('.dll'):
                    dest = os.path.join(bin_dir, basename)
                    with z.open(member) as src, open(dest, 'wb') as dst:
                        dst.write(src.read())
                    extracted.append(basename)
            if 'llama-server.exe' in extracted:
                print(f'  SUCCESS: llama-server.exe extracted to {bin_dir}')
                print(f'  Also extracted: {[f for f in extracted if f != \"llama-server.exe\"]}')
                sys.exit(0)
            else:
                print(f'  llama-server.exe not found in archive. Files: {extracted}')
    except Exception as e:
        print(f'  FAILED ({label}): {e}')

print('ERROR: Could not download any build.')
sys.exit(1)
"

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Download failed. Check your internet connection.
    echo.
    echo Alternative: If Ollama is installed on this PC, Hecos will
    echo automatically reuse its bundled llama-server.exe without
    echo needing to download anything.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo  SUCCESS! llama-server.exe is now in: %BIN_DIR%
echo ================================================================
echo.
echo Hecos will automatically use this binary when you select
echo a .gguf model with the Llama CPP backend.
echo Ollama does NOT need to be installed or running.
echo.
pause
