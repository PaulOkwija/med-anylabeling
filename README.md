<p align="center">
  <img alt="Med-AnyLabeling" style="width: 128px; height: 128px;" src="https://github.com/user-attachments/assets/847e47e6-acf0-4f96-9ed9-5485ab405ae0"/>
  <h1 align="center">Med-AnyLabeling</h1>
  <p align="center">Model-assisted segmentation labeling for medical imaging — with timing analytics to measure annotation efficiency.</p>
  <p align="center"><b>Forked from <a href="https://github.com/vietanhdev/anylabeling">AnyLabeling</a> by Viet-Anh Nguyen. Adapted for medical imaging research by <a href="https://github.com/PaulOkwija">PaulOkwija</a>.</b></p>
</p>

---

## What Is This?

**Med-AnyLabeling** is a streamlined, AI-assisted image annotation tool purpose-built for **medical imaging segmentation** workflows. It is a focused fork of [AnyLabeling](https://github.com/vietanhdev/anylabeling), with the UI simplified and extended with features specific to clinical and research annotation:

- **Session timing** — track and compare time-per-image between manual vs. model-assisted approaches
- **Medical imaging focus** — simplified interface that keeps segmentation workflows front-and-center
- **SAM-family models** (SAM, SAM 2, SAM 2.1, MobileSAM) for one-click organ/lesion segmentation
- **Standalone executable** — ships as a single `.exe` that requires zero prior installation on any Windows machine

---

## Key Features

- [x] Polygon, rectangle, and freeform segmentation annotation
- [x] **AI-assisted labeling** with SAM / SAM 2 / SAM 2.1 / MobileSAM (point & bounding-box prompts)
- [x] **Session timer** — records wall-clock time per image and per session, exportable as CSV for efficiency analysis
- [x] **Approach comparison** — tag a session as "manual" or "model-assisted" and compare annotation throughput
- [x] Auto-labeling with **YOLOv8** (object detection / bounding boxes)
- [x] DICOM-friendly grayscale rendering pipeline
- [x] JSON label export compatible with downstream segmentation training pipelines

### Supported AI Models

| Model | Prompt Types | Notes |
|-------|-------------|-------|
| SAM ViT-B / ViT-L / ViT-H | Point, Rectangle | Original Segment Anything |
| MobileSAM | Point, Rectangle | Lightweight — fast on CPU |
| SAM 2 Hiera-Tiny / Small / Base+ / Large | Point, Rectangle | Meta SAM 2 |
| SAM 2.1 Hiera-Tiny / Small / Base+ / Large | Point, Rectangle | Improved SAM 2 |
| YOLOv8n / s / m / l / x | — | Object detection & auto-labeling |

> Models are downloaded automatically on first use from Hugging Face. No manual setup required.

---

## Quickstart — Standalone Executable (Recommended)

The easiest way to use Med-AnyLabeling on any Windows computer:

1. Download `Med-AnyLabeling.exe` from [Releases](../../releases).
2. Double-click to run — no Python, no pip, no dependencies needed.
3. Open an image folder and start labeling.

See **[Building Your Own Executable](docs/build_executable.md)** if you want to compile it yourself or distribute to a team.

---

## Install from Source

**Requirements:** Python 3.11+. Recommended: Python 3.12 via [Miniconda](https://docs.conda.io/en/latest/miniconda.html).

```bash
# Create environment
conda create -n med-anylabeling python=3.12
conda activate med-anylabeling

# Install in editable mode (CPU)
pip install -e ".[dev]"

# Run the app
python anylabeling/app.py
```

For GPU acceleration (Windows/Linux):

```bash
pip install -e ".[gpu,dev]"
```

---

## Development

### 1. Set up the environment

```bash
conda create -n med-anylabeling python=3.12
conda activate med-anylabeling

# Editable install — code changes take effect without reinstalling
pip install -e ".[dev]"
```

> On macOS (Apple Silicon) you also need: `conda install -c conda-forge pyqt=6`

### 2. Run the app

```bash
python anylabeling/app.py
```

Open a specific image or label file directly:

```bash
python anylabeling/app.py path/to/image.png
python anylabeling/app.py path/to/labels.json
```

### 3. Useful dev flags

| Flag | Effect |
|------|--------|
| `--reset-config` | Wipe `~/.anylabelingrc` and start fresh — useful when config schema changes |
| `--logger-level debug` | Verbose logging (options: `debug`, `info`, `warning`, `error`, `fatal`) |
| `--config path/to/config.yaml` | Load a custom config instead of the user default |
| `--output /tmp/labels` | Write all label files to a specific directory |
| `--autosave` | Save labels automatically on every image change |
| `--nosortlabels` | Preserve insertion order in the label list (skip alphabetical sort) |
| `--nodata` | Skip embedding image data in JSON exports (keeps files small) |

Example — start clean with debug logging:

```bash
python anylabeling/app.py --reset-config --logger-level debug
```

### 4. Lint, format & test

```bash
# Check and auto-fix style
ruff check . --fix
ruff format .

# Run the full test suite
python -m unittest discover -s tests -v
```

Model inference tests (`tests/test_real_inference.py`) are skipped automatically when model
weights are not present under `~/anylabeling_data/models/`.

### 5. Config & data locations

| Path | Contents |
|------|----------|
| `~/.anylabelingrc` | Persisted UI state (zoom, recent files, window size, …) |
| `~/anylabeling_data/models/` | Downloaded ONNX model weights |
| `anylabeling/configs/auto_labeling/models.yaml` | Model catalog — edit here to add/remove models |

See [CLAUDE.md](CLAUDE.md) for the full developer guide: architecture notes, adding new models, and the pre-publish checklist.

---

## Build Standalone Executable

See **[docs/build_executable.md](docs/build_executable.md)** for complete step-by-step instructions to produce a zero-dependency `.exe`.

Short version (Windows):

```powershell
pip install -r requirements-dev.txt
pyinstaller anylabeling.spec
# Output: dist/anylabeling.exe
```

---

## Credits & Attribution

This project is a fork of **[AnyLabeling](https://github.com/vietanhdev/anylabeling)** by [Viet-Anh Nguyen](https://github.com/vietanhdev), licensed under GPL-3.0.

Additional upstream components:
- Labeling UI concepts from [LabelImg](https://github.com/heartexlabs/labelImg) and [LabelMe](https://github.com/wkentaro/labelme)
- Segmentation via [Segment Anything](https://segment-anything.com/) (SAM, SAM 2, SAM 2.1), [MobileSAM](https://github.com/ChaoningZhang/MobileSAM)
- Object detection via [YOLOv8](https://github.com/ultralytics/ultralytics)

**Fork maintainer:** [PaulOkwija](https://github.com/PaulOkwija)

---

## License

GPL-3.0 — see [LICENSE](LICENSE).
