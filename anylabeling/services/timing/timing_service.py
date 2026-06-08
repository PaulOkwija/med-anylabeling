"""
Session timing service for annotation efficiency tracking.

Records wall-clock time per image and per session. Persists session state
as a JSON file alongside label data so progress survives app restarts.
"""

import csv
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Optional


REVIEW_PENDING = "pending"
REVIEW_APPROVED = "approved"
REVIEW_NEEDS_REVISION = "needs_revision"


@dataclass
class ImageRecord:
    filename: str
    start_ts: float        # unix timestamp
    end_ts: Optional[float] = None
    shape_count: int = 0   # shapes saved when image was committed
    review_status: str = REVIEW_PENDING   # pending | approved | needs_revision
    note: str = ""

    @property
    def duration(self) -> float:
        """Elapsed seconds, or time-so-far if still open."""
        end = self.end_ts if self.end_ts is not None else time.monotonic_ns() / 1e9
        return max(0.0, end - self.start_ts)

    def is_complete(self) -> bool:
        return self.end_ts is not None


@dataclass
class Session:
    session_id: str
    name: str
    folder: str
    mode: str                          # "manual" | "ai-assisted"
    created_at: str                    # ISO 8601
    image_records: dict = field(default_factory=dict)   # filename → ImageRecord dict

    # --- persistence ---------------------------------------------------------

    def save(self, path: str) -> None:
        data = asdict(self)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> "Session":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        records = {
            k: ImageRecord(**v) for k, v in data.pop("image_records", {}).items()
        }
        session = cls(**data)
        session.image_records = records
        return session

    @classmethod
    def create(cls, name: str, folder: str, mode: str) -> "Session":
        return cls(
            session_id=str(uuid.uuid4()),
            name=name,
            folder=folder,
            mode=mode,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class TimingService:
    """
    Singleton that owns the active session and per-image timing state.

    Usage:
        svc = TimingService.instance()
        svc.start_image("/path/to/img.png")
        ...user annotates...
        svc.commit_image("/path/to/img.png", shape_count=3)
        svc.export_csv("/path/to/session.csv")
    """

    _instance: Optional["TimingService"] = None

    @classmethod
    def instance(cls) -> "TimingService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._session: Optional[Session] = None
        self._current_filename: Optional[str] = None
        self._image_start_mono: Optional[float] = None  # monotonic, for elapsed calc
        self._session_path: Optional[str] = None        # where session JSON lives

    # --- session lifecycle ---------------------------------------------------

    def new_session(self, name: str, folder: str, mode: str) -> Session:
        self._session = Session.create(name, folder, mode)
        self._session_path = os.path.join(folder, ".anylabeling_session.json")
        self._save()
        return self._session

    def open_session(self, path: str) -> Session:
        self._session = Session.load(path)
        self._session_path = path
        return self._session

    def close_session(self) -> None:
        if self._session and self._current_filename:
            self._finalize_current(shape_count=0)
        self._save()
        self._session = None
        self._session_path = None
        self._current_filename = None

    @property
    def active(self) -> bool:
        return self._session is not None

    @property
    def session(self) -> Optional[Session]:
        return self._session

    def set_mode(self, mode: str) -> None:
        """Switch session mode (manual / ai-assisted) mid-session."""
        if self._session:
            self._session.mode = mode
            self._save()

    # --- per-image timing ----------------------------------------------------

    def start_image(self, filename: str) -> None:
        """Call when a new image is loaded into the canvas."""
        if not self._session:
            return
        if self._current_filename and self._current_filename != filename:
            self._finalize_current(shape_count=0)

        self._current_filename = filename
        self._image_start_mono = time.monotonic()

        key = os.path.basename(filename)
        if key not in self._session.image_records:
            self._session.image_records[key] = ImageRecord(
                filename=filename,
                start_ts=time.time(),
            )

    def commit_image(self, filename: str, shape_count: int = 0) -> None:
        """Call when the user saves labels for the current image."""
        if not self._session:
            return
        key = os.path.basename(filename)
        rec = self._session.image_records.get(key)
        if rec and not rec.is_complete():
            rec.end_ts = time.time()
            rec.shape_count = shape_count
            self._save()

    def _finalize_current(self, shape_count: int) -> None:
        if self._current_filename:
            self.commit_image(self._current_filename, shape_count)

    # --- query ---------------------------------------------------------------

    @property
    def current_image_elapsed(self) -> float:
        """Seconds spent on the currently-open image."""
        if self._image_start_mono is None:
            return 0.0
        return time.monotonic() - self._image_start_mono

    @property
    def session_elapsed(self) -> float:
        """Total labelled seconds across all completed images in this session."""
        if not self._session:
            return 0.0
        return sum(
            r.duration for r in self._session.image_records.values() if r.is_complete()
        )

    @property
    def completed_count(self) -> int:
        if not self._session:
            return 0
        return sum(1 for r in self._session.image_records.values() if r.is_complete())

    @property
    def images_per_hour(self) -> float:
        elapsed = self.session_elapsed
        if elapsed <= 0 or self.completed_count == 0:
            return 0.0
        return (self.completed_count / elapsed) * 3600

    # --- export --------------------------------------------------------------

    def export_csv(self, path: str) -> None:
        if not self._session:
            raise RuntimeError("No active session to export.")
        rows = []
        for rec in self._session.image_records.values():
            rows.append(
                {
                    "session_id": self._session.session_id,
                    "session_name": self._session.name,
                    "mode": self._session.mode,
                    "filename": os.path.basename(rec.filename),
                    "duration_seconds": f"{rec.duration:.2f}",
                    "shape_count": rec.shape_count,
                    "complete": rec.is_complete(),
                    "review_status": rec.review_status,
                    "note": rec.note,
                    "start_time": datetime.fromtimestamp(rec.start_ts).isoformat(),
                }
            )
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else [])
            writer.writeheader()
            writer.writerows(rows)

    # --- internal ------------------------------------------------------------

    def _save(self) -> None:
        if self._session and self._session_path:
            try:
                self._session.save(self._session_path)
            except OSError:
                pass  # non-fatal — session state lives in memory
