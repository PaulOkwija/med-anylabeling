"""
Session dialog — create a new annotation session or resume an existing one.
"""

import os

from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from anylabeling.services.timing import TimingService


class SessionDialog(QDialog):
    """
    Modal dialog shown when the user opens a folder.

    Choices:
      • New session  — enter a name and mode, creates .anylabeling_session.json
      • Resume       — pick an existing .anylabeling_session.json
      • Skip         — continue without session tracking
    """

    def __init__(self, folder: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotation Session")
        self.setMinimumWidth(420)
        self._folder = folder
        self._result_mode = "skip"   # "new" | "resume" | "skip"

        self._build_ui()
        self._detect_existing_session()

    # -------------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # -- folder label --
        folder_label = QLabel(f"<b>Folder:</b> {self._folder}")
        folder_label.setWordWrap(True)
        layout.addWidget(folder_label)

        # -- NEW SESSION group --
        new_box = QGroupBox("Start a new session")
        new_layout = QFormLayout(new_box)

        self._rb_new = QRadioButton()
        self._rb_new.setChecked(True)
        self._rb_new.toggled.connect(self._update_state)
        new_box.setTitle("")   # title set via radio below

        name_row = QHBoxLayout()
        name_row.addWidget(self._rb_new)
        name_row.addWidget(QLabel("New session"))
        name_row.addStretch()

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Batch-01 manual")

        self._rb_manual = QRadioButton("Manual")
        self._rb_manual.setChecked(True)
        self._rb_ai = QRadioButton("AI-assisted")
        mode_row = QHBoxLayout()
        mode_row.addWidget(self._rb_manual)
        mode_row.addWidget(self._rb_ai)
        mode_row.addStretch()

        new_form = QFormLayout()
        new_form.addRow("Session name:", self._name_edit)
        new_form.addRow("Mode:", mode_row)

        new_outer = QVBoxLayout()
        new_outer.addLayout(name_row)
        new_outer.addLayout(new_form)
        new_box.setLayout(new_outer)
        layout.addWidget(new_box)

        # -- RESUME SESSION group --
        resume_box = QGroupBox()
        resume_outer = QVBoxLayout()

        resume_header = QHBoxLayout()
        self._rb_resume = QRadioButton("Resume existing session")
        self._rb_resume.toggled.connect(self._update_state)
        resume_header.addWidget(self._rb_resume)
        resume_header.addStretch()

        resume_path_row = QHBoxLayout()
        self._resume_path_edit = QLineEdit()
        self._resume_path_edit.setReadOnly(True)
        self._resume_path_edit.setPlaceholderText("No session file selected")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_session)
        resume_path_row.addWidget(self._resume_path_edit)
        resume_path_row.addWidget(browse_btn)

        resume_outer.addLayout(resume_header)
        resume_outer.addLayout(resume_path_row)
        resume_box.setLayout(resume_outer)
        layout.addWidget(resume_box)

        # -- SKIP --
        skip_row = QHBoxLayout()
        self._rb_skip = QRadioButton("Skip — annotate without session tracking")
        self._rb_skip.toggled.connect(self._update_state)
        skip_row.addWidget(self._rb_skip)
        layout.addLayout(skip_row)

        # -- buttons --
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._update_state()

    def _detect_existing_session(self):
        """Pre-fill resume path if a session file exists in the folder."""
        candidate = os.path.join(self._folder, ".anylabeling_session.json")
        if os.path.isfile(candidate):
            self._resume_path_edit.setText(candidate)
            self._rb_resume.setChecked(True)

    def _update_state(self):
        is_new = self._rb_new.isChecked()
        is_resume = self._rb_resume.isChecked()
        self._name_edit.setEnabled(is_new)
        self._rb_manual.setEnabled(is_new)
        self._rb_ai.setEnabled(is_new)
        self._resume_path_edit.setEnabled(is_resume)

    def _browse_session(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open session file",
            self._folder,
            "Session files (*.anylabeling_session.json *.json)",
        )
        if path:
            self._resume_path_edit.setText(path)
            self._rb_resume.setChecked(True)

    def _accept(self):
        svc = TimingService.instance()

        if self._rb_new.isChecked():
            name = self._name_edit.text().strip() or "Unnamed session"
            mode = "ai-assisted" if self._rb_ai.isChecked() else "manual"
            svc.new_session(name=name, folder=self._folder, mode=mode)
            self._result_mode = "new"

        elif self._rb_resume.isChecked():
            path = self._resume_path_edit.text().strip()
            if not os.path.isfile(path):
                QtWidgets.QMessageBox.warning(
                    self, "File not found", f"Cannot find session file:\n{path}"
                )
                return
            try:
                svc.open_session(path)
            except Exception as exc:
                QtWidgets.QMessageBox.warning(
                    self, "Load error", f"Could not load session:\n{exc}"
                )
                return
            self._result_mode = "resume"

        else:
            self._result_mode = "skip"

        self.accept()

    @property
    def result_mode(self) -> str:
        """'new' | 'resume' | 'skip'"""
        return self._result_mode
