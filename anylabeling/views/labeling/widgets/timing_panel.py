"""
Timing panel — sidebar dock that shows live session and per-image timing stats.

Updates every second via a QTimer. Reads from TimingService (singleton).
"""

from PyQt6 import QtCore, QtWidgets
from PyQt6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from anylabeling.services.timing import TimingService
from .session_review_dialog import SessionReviewDialog


def _fmt_seconds(seconds: float) -> str:
    """Format a duration as H:MM:SS."""
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h}:{m:02d}:{s:02d}"


class TimingPanel(QWidget):
    """
    Collapsible widget that shows session timing info.
    Intended to be placed inside a QDockWidget in LabelingWidget.
    """

    mode_changed = QtCore.pyqtSignal(str)          # emitted when user toggles mode
    navigate_to_image = QtCore.pyqtSignal(str)     # forwarded from review dialog

    def __init__(self, parent=None):
        super().__init__(parent)
        self._svc = TimingService.instance()
        self._build_ui()

        self._tick_timer = QtCore.QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._refresh)
        self._tick_timer.start()

        self._refresh()

    # -------------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        # -- session header --
        self._session_label = QLabel("No active session")
        self._session_label.setWordWrap(True)
        self._session_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        root.addWidget(self._session_label)

        # -- mode badge --
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self._mode_label = QLabel("—")
        self._mode_label.setStyleSheet(
            "padding: 2px 6px; border-radius: 4px; font-size: 11px;"
        )
        mode_row.addWidget(self._mode_label)
        mode_row.addStretch()
        self._toggle_mode_btn = QPushButton("Switch")
        self._toggle_mode_btn.setFixedWidth(60)
        self._toggle_mode_btn.clicked.connect(self._toggle_mode)
        mode_row.addWidget(self._toggle_mode_btn)
        root.addLayout(mode_row)

        # -- stats group --
        stats_box = QGroupBox("Current session")
        stats_layout = QFormLayout(stats_box)
        stats_layout.setHorizontalSpacing(12)

        self._img_elapsed_label = QLabel("—")
        self._session_elapsed_label = QLabel("—")
        self._completed_label = QLabel("—")
        self._rate_label = QLabel("—")

        stats_layout.addRow("This image:", self._img_elapsed_label)
        stats_layout.addRow("Session total:", self._session_elapsed_label)
        stats_layout.addRow("Completed:", self._completed_label)
        stats_layout.addRow("Rate:", self._rate_label)

        root.addWidget(stats_box)

        # -- actions --
        btn_row = QHBoxLayout()
        self._review_btn = QPushButton("Review & Export")
        self._review_btn.setToolTip("Review annotations and export labels")
        self._review_btn.clicked.connect(self._open_review)
        self._close_session_btn = QPushButton("End session")
        self._close_session_btn.clicked.connect(self._end_session)
        btn_row.addWidget(self._review_btn)
        btn_row.addWidget(self._close_session_btn)
        root.addLayout(btn_row)

        root.addStretch()

    # -------------------------------------------------------------------------

    def _refresh(self):
        svc = self._svc
        active = svc.active

        self._toggle_mode_btn.setEnabled(active)
        self._review_btn.setEnabled(active)
        self._close_session_btn.setEnabled(active)

        if not active:
            self._session_label.setText("No active session")
            self._mode_label.setText("—")
            self._mode_label.setStyleSheet(
                "padding: 2px 6px; border-radius: 4px; font-size: 11px;"
            )
            self._img_elapsed_label.setText("—")
            self._session_elapsed_label.setText("—")
            self._completed_label.setText("—")
            self._rate_label.setText("—")
            return

        session = svc.session
        self._session_label.setText(session.name)

        mode = session.mode
        color = "#2d7d46" if mode == "manual" else "#1a5c99"
        self._mode_label.setText(mode.capitalize())
        self._mode_label.setStyleSheet(
            f"padding: 2px 8px; border-radius: 4px; font-size: 11px;"
            f"background: {color}; color: white;"
        )
        self._toggle_mode_btn.setText(
            "→ AI" if mode == "manual" else "→ Manual"
        )

        self._img_elapsed_label.setText(_fmt_seconds(svc.current_image_elapsed))
        self._session_elapsed_label.setText(_fmt_seconds(svc.session_elapsed))
        self._completed_label.setText(str(svc.completed_count))
        rate = svc.images_per_hour
        self._rate_label.setText(f"{rate:.1f} img/hr" if rate > 0 else "—")

    def _toggle_mode(self):
        svc = self._svc
        if not svc.active:
            return
        new_mode = "ai-assisted" if svc.session.mode == "manual" else "manual"
        svc.set_mode(new_mode)
        self.mode_changed.emit(new_mode)
        self._refresh()

    def _open_review(self):
        if not self._svc.active:
            return
        folder = self._svc.session.folder if self._svc.session else ""
        dlg = SessionReviewDialog(current_folder=folder, parent=self)
        dlg.navigate_to_image.connect(self.navigate_to_image)
        dlg.exec()

    def _end_session(self):
        svc = self._svc
        if not svc.active:
            return
        reply = QtWidgets.QMessageBox.question(
            self,
            "End session",
            "End and save the current session?",
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No,
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            svc.close_session()
            self._refresh()
