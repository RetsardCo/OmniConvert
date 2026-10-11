"""Initial baseline engines: DataEngine (CSV/JSON) and PillowEngine stub."""

from pathlib import Path
import json
import csv
from typing import Callable, Optional

from omniconvert.engines.base import BaseEngine
from omniconvert.models.conversion_job import ConversionJob, JobProgress

class DataEngine(BaseEngine):
    """Handles structured data conversion (CSV <-> JSON)."""

    @property
    def name(self) -> str:
        return "data"

    def is_available(self) -> bool:
        return True

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        if is_cancelled and is_cancelled():
            raise InterruptedError("Job cancelled before start.")

        if progress_callback:
            progress_callback(JobProgress(percentage=10.0, stage="Parsing", detail="Reading source data"))

        target_file = workspace_dir / f"{job.source_path.stem}.{job.target_format}"

        if job.operation_id == "data.csv_to_json":
            with open(job.source_path, "r", encoding="utf-8", errors="replace") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if is_cancelled and is_cancelled():
                raise InterruptedError("Job cancelled during processing.")

            if progress_callback:
                progress_callback(JobProgress(percentage=70.0, stage="Serializing", detail="Writing JSON"))

            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(rows, f, indent=2)

        elif job.operation_id == "data.json_to_csv":
            with open(job.source_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                if isinstance(data, dict):
                    data = [data]
                else:
                    raise ValueError("JSON must contain an array or object to convert to CSV.")

            if is_cancelled and is_cancelled():
                raise InterruptedError("Job cancelled during processing.")

            if progress_callback:
                progress_callback(JobProgress(percentage=70.0, stage="Serializing", detail="Writing CSV"))

            fieldnames = []
            for item in data:
                if isinstance(item, dict):
                    for k in item.keys():
                        if k not in fieldnames:
                            fieldnames.append(k)

            with open(target_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for item in data:
                    if isinstance(item, dict):
                        # Flatten complex nested objects as JSON string
                        flat_row = {
                            k: json.dumps(v) if isinstance(v, (dict, list)) else v
                            for k, v in item.items()
                        }
                        writer.writerow(flat_row)

        if progress_callback:
            progress_callback(JobProgress(percentage=100.0, stage="Complete", detail="Data converted"))

        return target_file
