# Coding Structure

**Med-AnyLabeling** — fork of [AnyLabeling](https://github.com/vietanhdev/anylabeling) by Viet-Anh Nguyen.
Maintained by [PaulOkwija](https://github.com/PaulOkwija) for medical imaging segmentation research.

## Source Layout

- **app.py** — entry point; constructs `QApplication` and `MainWindow`
- **app_info.py** — version, app name, CPU/GPU preference flag
- **views/** — PyQt6 UI classes (`MainWindow`, `LabelingWidget`, `Canvas`, etc.)
- **services/** — independent backend services:
  - `auto_labeling/` — model registry, model manager, ONNX runners (SAM, YOLOv8)
  - `timing/` — session timer for annotation efficiency tracking *(fork addition)*
- **configs/** — YAML configuration files (model catalog, default settings)
- **resources/** — Qt resources (icons, translations, compiled `resources.py`)
- **utils.py** — shared utility functions
