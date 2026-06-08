# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Identity

**Med-AnyLabeling** is a focused fork of [AnyLabeling](https://github.com/vietanhdev/anylabeling) (by Viet-Anh Nguyen), maintained by [PaulOkwija](https://github.com/PaulOkwija).

**Fork goals:**
1. Streamlined UI/UX for medical imaging segmentation workflows
2. Session timing analytics (compare manual vs. model-assisted annotation speed)
3. Distributable as a standalone Windows executable (zero-dependency)

The underlying engine is unchanged: PyQt6 desktop app with an ONNX auto-labeling backend running SAM 1/2/2.1, MobileSAM, and YOLOv8 models.

---

## Common Commands

```bash
# Run the app from source
python anylabeling/app.py

# Editable install for development (CPU)
pip install -e ".[dev]"
# GPU:   pip install -e ".[gpu,dev]"
# macOS: pip install -e ".[macos,dev]"  # plus: conda install -c conda-forge pyqt=6

# Lint + format (ruff config is in pyproject.toml)
ruff check .
ruff format .

# Run all tests
python -m unittest discover -s tests -v

# Build standalone executable (Windows)
pip install -r requirements-dev.txt
pyinstaller anylabeling.spec
# Output: dist/anylabeling.exe
```

App-level CLI flags: `--reset-config`, `--logger-level {debug,info,warning,error,fatal}`,
`--config <path>`, `--output / -O / -o`, `--nodata`, `--autosave`, `--nosortlabels`,
`--flags`, plus a positional `filename` (image or label file). Default user config
lives at `~/.anylabelingrc`.

---

## High-Level Architecture

### Entry Point and UI Tree

`anylabeling/app.py` sets `MKL/NUMEXPR/OMP_NUM_THREADS=1` (workaround for a macOS-M1
bus error in `np.linalg.solve`) before any heavy imports, then constructs a `QApplication`
and a `MainWindow`. The UI tree is intentionally shallow:

```
MainWindow                          (anylabeling/views/mainwindow.py)
└── LabelingWrapper                 (anylabeling/views/labeling/label_wrapper.py)
    └── LabelingWidget              (anylabeling/views/labeling/label_widget.py, ~3.2k LOC)
        ├── Canvas                  (anylabeling/views/labeling/widgets/canvas.py)
        ├── AutoLabelingWidget      (drives ModelManager from the UI side)
        ├── LabelDialog / Brightness / FileDialogPreview / ZoomWidget …
        └── ExportDialog
```

`LabelingWidget` is the "god widget" — it owns the file list, the canvas, the
toolbars, the shape list, the label list, file I/O, undo/redo, and most keybindings.
When in doubt, that file is where things live.

### Fork-Specific Modules

The following modules are additions to the upstream codebase:

- `anylabeling/services/timing/` — session timer service (records per-image and
  per-session wall-clock time; exports CSV); exposes `TimingService` singleton.
- `anylabeling/views/labeling/widgets/timing_panel.py` — collapsible timing panel
  in the sidebar showing elapsed time, images/hour, and session mode (manual vs. AI).

### Auto-Labeling Pipeline

```
anylabeling/services/auto_labeling/
├── registry.py          # @ModelRegistry.register("yolov8") decorator → singleton dict
├── model.py             # abstract Model(QObject); predict_shapes() returns AutoLabelingResult
├── model_manager.py     # ModelManager(QObject): loads models.yaml, downloads weights,
│                        # dispatches predict_shapes_threading()
├── types.py             # AutoLabelingResult, AutoLabelingMode (point/rectangle, ADD/REMOVE)
├── lru_cache.py         # image-embedding cache for SAM-family models
├── segment_anything.py  # variant detector — picks SAM1/SAM2 from ONNX inputs/config
├── sam_onnx.py          # SAM1 / MobileSAM ONNX runner
├── sam2_onnx.py         # SAM2 ONNX runner
└── yolov8.py
```

Two registry-relevant facts:

- Concrete models register themselves via `@ModelRegistry.register("type-name")`
  at import time. `anylabeling/services/auto_labeling/__init__.py` imports every
  module so the side-effects fire — adding a new model means importing it here too.
- `models.yaml` (`anylabeling/configs/auto_labeling/models.yaml`) is the catalog
  the UI reads. Each entry has `name`, `display_name`, `type` (matches a registry
  key), `download_url`, plus model-specific fields. New model = add an entry here
  *and* a registered class.

Weights live under `~/anylabeling_data/models/<name>/` after first download.

### CPU / GPU / macOS Packaging

Static metadata is in `pyproject.toml`. `setup.py` reads `__preferred_device__`
from `anylabeling/app_info.py` and, when set to `"GPU"` on non-Darwin, overrides
the package name to `anylabeling-gpu` and swaps `onnxruntime` for `onnxruntime-gpu`.

---

## Building the Standalone Executable

See [docs/build_executable.md](docs/build_executable.md) for step-by-step instructions.
The goal is a single `Med-AnyLabeling.exe` that runs on any Windows machine without
Python installed.

Key points:
- Uses PyInstaller via `anylabeling.spec`
- ONNX runtime DLLs are bundled explicitly (the spec handles this)
- First launch downloads model weights from Hugging Face into `~/anylabeling_data/`
- Build from a clean venv to avoid bundling dev-only packages

---

## Tests

`tests/` is plain `unittest`. Notable files:

- `tests/test_label_colormap.py` — regression for imgviz>=2.0 read-only colormap (#227)
- `tests/test_real_inference.py` — end-to-end ONNX inference for SAM1/SAM2/YOLOv8.
  Each class skips when model files are not under `~/anylabeling_data/models/`.

---

## Pre-Publish Checklist

Run these **before tagging a release**. CI gates are in `.github/workflows/tests.yml`.

### 1. Fresh-venv install with latest deps

```bash
python -m venv /tmp/med-al-check
/tmp/med-al-check/bin/pip install --upgrade pip
/tmp/med-al-check/bin/pip install .
```

### 2. Run the full unittest suite

```bash
/tmp/med-al-check/bin/python -m unittest discover -s tests -v
```

### 3. Smoke-test the import chain

```bash
QT_QPA_PLATFORM=offscreen /tmp/med-al-check/bin/python -c "
from anylabeling.views.labeling import label_widget
from anylabeling import app
print('startup imports OK')
"
```

### 4. Build and test the executable

```powershell
pip install -r requirements-dev.txt
pyinstaller anylabeling.spec
./dist/anylabeling.exe   # verify it opens and loads a sample DICOM/PNG
```

---

## UI/UX Design Principles (Fork-Specific)

1. **Medical imaging first** — every UI decision should reduce cognitive load during
   high-volume annotation sessions. Remove features not relevant to segmentation.
2. **Timing is a first-class feature** — always visible, never intrusive.
3. **Simplify, don't add** — when in doubt, remove a panel or menu item rather than
   adding one. Prefer keyboard shortcuts for power users.
4. **No internet required at runtime** — models must be bundled or cached locally;
   do not add features that require a live API call during annotation.

---

## Why This Fork Exists

The upstream AnyLabeling is a general-purpose labeling tool. This fork narrows the
scope to medical imaging segmentation research with two additions not present upstream:

1. **Timing analytics** — research comparing manual vs. AI-assisted annotation
   requires reproducible time measurements. This is built into the session workflow.
2. **Zero-dependency executable** — clinical environments often cannot run Python.
   The compiled executable removes all installation friction.

Upstream AnyLabeling credit: Viet-Anh Nguyen (https://github.com/vietanhdev/anylabeling)
