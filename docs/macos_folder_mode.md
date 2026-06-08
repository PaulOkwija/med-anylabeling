# macOS Build for Med-AnyLabeling

> **Note:** The macOS build is provided as a directory bundle rather than a single
> `.app` file. This is intentional — it allows easier customization and better
> compatibility across macOS versions.

---

## Running a Pre-Built Release

1. Download `Med-AnyLabeling-macOS.zip` from [Releases](../../releases).

2. Extract the zip:

   ```bash
   unzip Med-AnyLabeling-macOS.zip
   ```

3. Run the application:

   ```bash
   cd Med-AnyLabeling-Folder
   ./anylabeling
   ```

---

## Building Locally (macOS)

### Prerequisites

- Python 3.12 via [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- PyQt6 via conda (PyPI's PyQt6 does not include the native macOS libs)

### Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/PaulOkwija/Med-AnyLabeling.git
   cd Med-AnyLabeling
   ```

2. Create and activate a conda environment:

   ```bash
   conda create -n med-anylabeling python=3.12
   conda activate med-anylabeling
   conda install -c conda-forge pyqt=6
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements-macos-dev.txt
   ```

4. Build:

   ```bash
   chmod +x scripts/build_macos_folder.sh
   ./scripts/build_macos_folder.sh        # CPU version
   # ./scripts/build_macos_folder.sh GPU  # GPU version (if applicable)
   ```

5. Output: `dist/AnyLabeling-Folder/`

---

## Troubleshooting

- **Permission denied on launch:**

  ```bash
  chmod +x Med-AnyLabeling-Folder/anylabeling
  ```

- **Dynamic library loading errors:**

  ```bash
  pip install -r requirements-macos.txt
  ```

- **Graphics / UI issues:** Use the CPU build.

- **Models not downloading:** Ensure `huggingface.co` is reachable. Models are
  stored in `~/anylabeling_data/models/` on first use.

---

*Original macOS build infrastructure from [AnyLabeling](https://github.com/vietanhdev/anylabeling) by Viet-Anh Nguyen.*