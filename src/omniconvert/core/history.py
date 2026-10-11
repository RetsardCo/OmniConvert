"""Persistent Conversion History Manager (stores metadata only, never file contents)."""

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import logging
from typing import List, Optional

from omniconvert.config.paths import get_history_path
from omniconvert.models.conversion_job import ConversionJob

logger = logging.getLogger(__name__)


@dataclass
class HistoryRecord:
    job_id: str
    operation_id: str
    engine: str
    source_name: str
    source_path: str
    destination_path: str
    target_format: str
    status: str
    started_at: str
    duration_seconds: float
    error_summary: str = ""
    warnings: str = ""


class HistoryManager:
    """Manages reading, appending, and clearing conversion history records on disk."""

    def __init__(self, history_file: Optional[Path] = None, max_records: int = 200):
        self.history_file = history_file or get_history_path()
        self.max_records = max_records

    def load_records(self) -> List[HistoryRecord]:
        if not self.history_file.exists():
            return []
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            records = []
            for item in data:
                if isinstance(item, dict):
                    valid_keys = {k: v for k, v in item.items() if k in HistoryRecord.__dataclass_fields__}
                    records.append(HistoryRecord(**valid_keys))
            return records
        except Exception as e:
            logger.warning("Failed to load history from %s: %s", self.history_file, e)
            return []

    def add_job(self, job: ConversionJob) -> HistoryRecord:
        duration = 0.0
        if job.started_at and job.finished_at:
            duration = round(max(0.0, (job.finished_at - job.started_at).total_seconds()), 2)

        started_str = job.started_at.strftime("%Y-%m-%d %H:%M:%S") if job.started_at else ""
        err_msg = job.error.message if job.error else ""
        if job.error and job.error.step:
            err_msg = f"[{job.error.step}] {err_msg}"

        rec = HistoryRecord(
            job_id=job.id,
            operation_id=job.operation_id,
            engine=job.engine,
            source_name=job.source_path.name,
            source_path=str(job.source_path),
            destination_path=str(job.destination_path or ""),
            target_format=job.target_format,
            status=job.state.value,
            started_at=started_str,
            duration_seconds=duration,
            error_summary=err_msg,
            warnings="; ".join(job.warnings) if job.warnings else ""
        )

        records = self.load_records()
        records.insert(0, rec)
        records = records[:self.max_records]
        self._save_records(records)
        return rec

    def clear(self) -> None:
        self._save_records([])

    def _save_records(self, records: List[HistoryRecord]) -> None:
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            self.history_file.write_text(
                json.dumps([asdict(r) for r in records], indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error("Failed to write conversion history: %s", e)
