# Building the Med-AnyLabeling Standalone Executable

This guide produces a single `Med-AnyLabeling.exe` that runs on **any Windows machine
without Python, pip, or any other installation** — download and double-click.

---

## Prerequisites (build machine only)

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11 or 3.12 | 3.12 recommended |
| Miniconda or venv | any | isolate the build environment |
| Git | any | to clone the repo |
| ~4 GB free disk | — | PyInstaller bundles everything |

---

## Step-by-Step Build (Windows)

### 1. Clone the repository

```powershell
git clone https://github.com/PaulOkwija/Med-AnyLabeling.git
cd Med-AnyLabeling
```

### 2. Create a clean build environment

> **Important:** always build from a clean virtual environment to avoid bundling
> dev-only packages (PySide6, build tools, etc.) into the executable.

```powershell
python -m venv .venv-build
.venv-build\Scripts\activate
```

### 3. Install build dependencies

```powershell
pip install --upgrade pip
pip install -r requirements-dev.txt
```

This installs PyInstaller and all runtime dependencies.

For **GPU support** (NVIDIA CUDA), install the GPU runtime instead:

```powershell
pip install onnxruntime-gpu>=1.20.0
```

### 4. Run PyInstaller

```powershell
pyinstaller anylabeling.spec
```

PyInstaller reads `anylabeling.spec` which:
- Bundles all Python code and dependencies
- Copies ONNX runtime DLLs to both expected locations
- Includes YAML config files and the auto-labeling UI file
- Disables the console window (`console=False`)

### 5. Collect the output

```
dist/
└── anylabeling.exe    ← this is your standalone executable
```

Rename it for distribution:

```powershell
Rename-Item dist\anylabeling.exe Med-AnyLabeling.exe
```

### 6. Test the executable

On the build machine:

```powershell
.\Med-AnyLabeling.exe
```

On a **fresh Windows machine** (no Python installed): copy `Med-AnyLabeling.exe`
and double-click. The first launch downloads AI model weights from Hugging Face
into `%USERPROFILE%\anylabeling_data\models\` — internet is only required once
per model.

---

## What Gets Bundled

| Component | Source | Bundled? |
|-----------|--------|----------|
| Python runtime | venv | ✅ |
| PyQt6 (UI framework) | pip | ✅ |
| ONNX runtime + DLLs | pip | ✅ |
| OpenCV | pip | ✅ |
| App configs (YAML) | `anylabeling/configs/` | ✅ |
| AI model weights | Hugging Face | ❌ downloaded on first use |

Model weights are **not** bundled — they are downloaded automatically on first use
into `%USERPROFILE%\anylabeling_data\models\`. This keeps the executable small
(~300 MB vs. several GB) and lets users choose which models they need.

---

## Offline / Air-Gapped Deployment

If the target machine has no internet access, pre-download model weights on a
connected machine and copy the folder:

```
%USERPROFILE%\anylabeling_data\models\
├── mobile_sam_20230629\
├── sam2_hiera_tiny_20240803\
└── yolov8n-r20230415\
```

Then copy this folder to the same path on the target machine before running the
executable. The app checks for local weights first and will not attempt a download
if they are already present.

---

## Troubleshooting

### "Failed to execute script" on launch

Run from PowerShell to see the error:

```powershell
.\Med-AnyLabeling.exe 2>&1
```

Common causes:
- Missing Visual C++ Redistributable — install [VC++ Redist](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- ONNX DLL not found — rebuild from a clean venv (step 2 above)

### App launches but models fail to download

Check internet access. Models are fetched from `huggingface.co`. If behind a
corporate proxy, set `HTTPS_PROXY` before launching:

```powershell
$env:HTTPS_PROXY="http://proxy.company.com:8080"
.\Med-AnyLabeling.exe
```

### Antivirus blocks the executable

PyInstaller executables are sometimes flagged as suspicious because they self-extract.
Add an exclusion for the executable in your AV settings, or sign the binary with a
code-signing certificate.

---

## Rebuilding After Code Changes

Always rebuild from a clean state to avoid stale caches:

```powershell
Remove-Item -Recurse -Force build, dist
pyinstaller anylabeling.spec
```

---

## macOS Build

See [macos_folder_mode.md](macos_folder_mode.md) for macOS-specific instructions.
The macOS build produces a folder bundle rather than a single binary.

---

*Original executable build infrastructure from [AnyLabeling](https://github.com/vietanhdev/anylabeling) by Viet-Anh Nguyen.*
