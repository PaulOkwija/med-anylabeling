"""
Session review dialog — lets the annotator inspect and sign off on every image
before the session is closed and labels are exported.

Layout
------
  Top:    Session summary bar (name, mode, total time, rate, counts)
  Middle: Table — one row per image (filename, time, shapes, status, notes)
  Bottom: Legend + action buttons (Go to Image | Export CSV | Export Labels | Close)

Status values: pending (grey), approved (green), needs_revision (amber)
"""

import os

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from anylabeling.services.timing import (
    REVIEW_APPROVED,
    REVIEW_NEEDS_REVISION,
    REVIEW_PENDING,
    TimingService,
)
from .export_dialog import ExportDialog


# Colours for status badges
_STATUS_COLORS = {
    REVIEW_PENDING:        ("#888888", "white"),
    REVIEW_APPROVED:       ("#2d7d46", "white"),
    REVIEW_NEEDS_REVISION: ("#c17f00", "white"),
}
_STATUS_LABELS = {
    REVIEW_PENDING:        "Pending",
    REVIEW_APPROVED:       "Approved",
    REVIEW_NEEDS_REVISION: "Needs revision",
}

# Table column indices
_COL_FILENAME  = 0
_COL_TIME      = 1
_COL_SHAPES    = 2
_COL_STATUS    = 3
_COL_NOTE      = 4


def _fmt_seconds(s: float) -> str:
    s = int(s)
    return f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


class _StatusButton(QPushButton):
    """Cycles through status values on each click."""

    _cycle = [REVIEW_PENDING, REVIEW_APPROVED, REVIEW_NEEDS_REVISION]
    status_changed = pyqtSignal(str, str)   # (filename, new_status)

    def __init__(self, filename: str, status: str, parent=None):
        super().__init__(parent)
        self._filename = filename
        self._status = status
        self._apply()
        self.clicked.connect(self._cycle_status)
        self.setFixedWidth(130)

    def _apply(self):
        bg, fg = _STATUS_COLORS[self._status]
        self.setText(_STATUS_LABELS[self._status])
        self.setStyleSheet(
            f"QPushButton {{"
            f"  background: {bg}; color: {fg};"
            f"  border-radius: 4px; padding: 2px 6px; font-size: 11px;"
            f"}}"
        )

    def _cycle_status(self):
        idx = self._cycle.index(self._status)
        self._status = self._cycle[(idx + 1) % len(self._cycle)]
        self._apply()
        self.status_changed.emit(self._filename, self._status)

    def current_status(self) -> str:
        return self._status


class SessionReviewDialog(QDialog):
    """
    Review all images in the active session before export.

    Signals
    -------
    navigate_to_image(str)  — emitted when user clicks "Go to Image"; caller
                              should load that file into the canvas.
    """

    navigate_to_image = pyqtSignal(str)

    def __init__(self, current_folder: str = "", parent=None):
        super().__init__(parent)
        self._svc = TimingService.instance()
        self._current_folder = current_folder
        self.setWindowTitle("Session Review")
        self.setMinimumSize(820, 520)
        self._build_ui()
        self._populate()

    # -------------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # -- summary bar --
        self._summary_group = QGroupBox("Session summary")
        summary_layout = QHBoxLayout(self._summary_group)

        self._lbl_name    = QLabel()
        self._lbl_mode    = QLabel()
        self._lbl_elapsed = QLabel()
        self._lbl_rate    = QLabel()
        self._lbl_counts  = QLabel()

        for lbl in (self._lbl_name, self._lbl_mode, self._lbl_elapsed,
                    self._lbl_rate, self._lbl_counts):
            lbl.setStyleSheet("font-size: 12px;")
            summary_layout.addWidget(lbl)
            summary_layout.addSpacing(20)

        summary_layout.addStretch()
        root.addWidget(self._summary_group)

        # -- filter bar --
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("filename…")
        self._filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter_edit)
        filter_row.addStretch()

        # legend
        for status in [REVIEW_PENDING, REVIEW_APPROVED, REVIEW_NEEDS_REVISION]:
            bg, fg = _STATUS_COLORS[status]
            badge = QLabel(_STATUS_LABELS[status])
            badge.setStyleSheet(
                f"background:{bg}; color:{fg}; border-radius:4px;"
                f"padding:2px 6px; font-size:10px;"
            )
            filter_row.addWidget(badge)

        root.addLayout(filter_row)

        # -- table --
        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["Filename", "Time", "Shapes", "Status", "Notes"]
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_FILENAME, QHeaderView.ResizeMode.Stretch
        )
        self._table.horizontalHeader().setSectionResizeMode(
            _COL_NOTE, QHeaderView.ResizeMode.Stretch
        )
        self._table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self._table.verticalHeader().hide()
        self._table.setAlternatingRowColors(True)
        root.addWidget(self._table)

        # -- bottom bar --
        bottom = QHBoxLayout()

        self._approve_all_btn = QPushButton("Approve all")
        self._approve_all_btn.clicked.connect(self._approve_all)

        self._go_btn = QPushButton("Go to image")
        self._go_btn.setToolTip("Open the selected image in the canvas")
        self._go_btn.clicked.connect(self._go_to_selected)

        self._export_csv_btn = QPushButton("Export timing CSV")
        self._export_csv_btn.clicked.connect(self._export_csv)

        self._export_labels_btn = QPushButton("Export labels…")
        self._export_labels_btn.setDefault(True)
        self._export_labels_btn.clicked.connect(self._export_labels)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)

        bottom.addWidget(self._approve_all_btn)
        bottom.addWidget(self._go_btn)
        bottom.addStretch()
        bottom.addWidget(self._export_csv_btn)
        bottom.addWidget(self._export_labels_btn)
        bottom.addWidget(close_btn)
        root.addLayout(bottom)

    # -------------------------------------------------------------------------
    # Populate / refresh
    # -------------------------------------------------------------------------

    def _populate(self):
        self._refresh_summary()

        session = self._svc.session
        if not session:
            return

        records = list(session.image_records.values())
        self._table.setRowCount(len(records))

        for row, rec in enumerate(records):
            name_item = QTableWidgetItem(os.path.basename(rec.filename))
            name_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            name_item.setData(Qt.ItemDataRole.UserRole, rec.filename)
            self._table.setItem(row, _COL_FILENAME, name_item)

            time_item = QTableWidgetItem(_fmt_seconds(rec.duration))
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            time_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(row, _COL_TIME, time_item)

            shapes_item = QTableWidgetItem(str(rec.shape_count))
            shapes_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            shapes_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            self._table.setItem(row, _COL_SHAPES, shapes_item)

            btn = _StatusButton(rec.filename, rec.review_status)
            btn.status_changed.connect(self._on_status_changed)
            self._table.setCellWidget(row, _COL_STATUS, btn)

            note_item = QTableWidgetItem(rec.note)
            self._table.setItem(row, _COL_NOTE, note_item)

        self._table.itemChanged.connect(self._on_note_changed)
        self._table.resizeRowsToContents()

    def _refresh_summary(self):
        svc = self._svc
        if not svc.active:
            self._summary_group.setTitle("No active session")
            return

        session = svc.session
        approved   = sum(1 for r in session.image_records.values()
                         if r.review_status == REVIEW_APPROVED)
        needs_rev  = sum(1 for r in session.image_records.values()
                         if r.review_status == REVIEW_NEEDS_REVISION)
        total      = len(session.image_records)

        self._lbl_name.setText(f"<b>{session.name}</b>")
        color = "#2d7d46" if session.mode == "manual" else "#1a5c99"
        self._lbl_mode.setText(
            f'<span style="background:{color};color:white;'
            f'border-radius:4px;padding:2px 6px;font-size:11px;">'
            f'{session.mode.capitalize()}</span>'
        )
        self._lbl_elapsed.setText(f"Total: {_fmt_seconds(svc.session_elapsed)}")
        rate = svc.images_per_hour
        self._lbl_rate.setText(f"{rate:.1f} img/hr" if rate > 0 else "Rate: —")
        self._lbl_counts.setText(
            f"Images: {total} | "
            f'<span style="color:#2d7d46;">✔ {approved}</span> | '
            f'<span style="color:#c17f00;">⚑ {needs_rev}</span> | '
            f'Pending: {total - approved - needs_rev}'
        )
        self._lbl_counts.setTextFormat(Qt.TextFormat.RichText)

    # -------------------------------------------------------------------------
    # Slots
    # -------------------------------------------------------------------------

    def _on_status_changed(self, filename: str, new_status: str):
        session = self._svc.session
        if not session:
            return
        key = os.path.basename(filename)
        rec = session.image_records.get(key)
        if rec:
            rec.review_status = new_status
            self._svc._save()
        self._refresh_summary()

    def _on_note_changed(self, item: QTableWidgetItem):
        if item.column() != _COL_NOTE:
            return
        row = item.row()
        name_item = self._table.item(row, _COL_FILENAME)
        if not name_item:
            return
        filename = os.path.basename(name_item.data(Qt.ItemDataRole.UserRole) or name_item.text())
        session = self._svc.session
        if not session:
            return
        rec = session.image_records.get(filename)
        if rec:
            rec.note = item.text()
            self._svc._save()

    def _apply_filter(self, text: str):
        text = text.lower()
        for row in range(self._table.rowCount()):
            item = self._table.item(row, _COL_FILENAME)
            visible = not text or (item and text in item.text().lower())
            self._table.setRowHidden(row, not visible)

    def _approve_all(self):
        session = self._svc.session
        if not session:
            return
        for row in range(self._table.rowCount()):
            btn = self._table.cellWidget(row, _COL_STATUS)
            if isinstance(btn, _StatusButton):
                while btn.current_status() != REVIEW_APPROVED:
                    btn._cycle_status()
        self._refresh_summary()

    def _go_to_selected(self):
        rows = self._table.selectedItems()
        if not rows:
            return
        row = rows[0].row()
        name_item = self._table.item(row, _COL_FILENAME)
        if not name_item:
            return
        full_path = name_item.data(Qt.ItemDataRole.UserRole) or name_item.text()
        self.navigate_to_image.emit(full_path)

    def _export_csv(self):
        svc = self._svc
        if not svc.active:
            return
        default = os.path.join(
            svc.session.folder if svc.session else "",
            f"{svc.session.name}.csv",
        )
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export timing CSV", default, "CSV (*.csv)"
        )
        if path:
            try:
                svc.export_csv(path)
                QtWidgets.QMessageBox.information(self, "Saved", f"CSV saved to:\n{path}")
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Error", str(exc))

    def _export_labels(self):
        session = self._svc.session
        pending_count = sum(
            1 for r in session.image_records.values()
            if r.review_status == REVIEW_PENDING
        ) if session else 0

        if pending_count:
            reply = QtWidgets.QMessageBox.question(
                self,
                "Unreviewed images",
                f"{pending_count} image(s) are still marked 'Pending'.\n"
                "Export anyway?",
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No,
            )
            if reply != QtWidgets.QMessageBox.StandardButton.Yes:
                return

        dlg = ExportDialog(parent=self, current_folder=self._current_folder)
        dlg.exec()
