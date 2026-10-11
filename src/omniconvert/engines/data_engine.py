"""Comprehensive Structured Data and Text Engine (JSON, YAML, XML, CSV, Encoding, and Line Endings)."""

from pathlib import Path
import json
import csv
import logging
from typing import Callable, Optional, Dict, Any, List
import yaml
import defusedxml.ElementTree as ET
import xml.etree.ElementTree as standard_ET

from omniconvert.engines.base import BaseEngine
from omniconvert.models.conversion_job import ConversionJob, JobProgress

logger = logging.getLogger(__name__)

class DataEngine(BaseEngine):
    """
    Engine for converting and transforming structured data and text formats:
    - CSV <-> JSON
    - JSON <-> YAML
    - XML <-> JSON
    - Line endings (CRLF <-> LF)
    - Character encoding (UTF-8, UTF-16, ASCII, Latin-1)
    """

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
            raise InterruptedError("Cancelled before execution.")

        source = job.source_path
        target_format = job.target_format.lower().lstrip(".")
        op = job.operation_id
        settings = job.settings or {}
        target_file = workspace_dir / f"{source.stem}.{target_format}"

        if progress_callback:
            progress_callback(JobProgress(percentage=10.0, stage="Reading Data", detail=f"Parsing {source.name}"))

        # 1. CSV to JSON
        if op == "data.csv_to_json":
            return self._csv_to_json(source, target_file, progress_callback, is_cancelled)

        # 2. JSON to CSV
        elif op == "data.json_to_csv":
            return self._json_to_csv(source, target_file, job, progress_callback, is_cancelled)

        # 3. JSON to YAML
        elif op == "data.json_to_yaml":
            return self._json_to_yaml(source, target_file, progress_callback, is_cancelled)

        # 4. YAML to JSON
        elif op == "data.yaml_to_json":
            return self._yaml_to_json(source, target_file, progress_callback, is_cancelled)

        # 5. XML to JSON
        elif op == "data.xml_to_json":
            return self._xml_to_json(source, target_file, progress_callback, is_cancelled)

        # 6. JSON to XML
        elif op == "data.json_to_xml":
            return self._json_to_xml(source, target_file, progress_callback, is_cancelled)

        # 7. Line Ending Conversion (CRLF <-> LF)
        elif op in ("text.to_crlf", "text.to_lf"):
            return self._convert_line_endings(source, target_file, (op == "text.to_crlf"), progress_callback)

        # 8. Character Encoding Conversion
        elif op == "text.convert_encoding":
            target_encoding = settings.get("encoding", "utf-8")
            return self._convert_encoding(source, target_file, target_encoding, progress_callback)

        raise NotImplementedError(f"Unsupported data operation: {op}")

    def _csv_to_json(self, source: Path, target: Path, progress_cb, is_cancelled) -> Path:
        with open(source, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled.")

        if progress_cb:
            progress_cb(JobProgress(percentage=70.0, stage="Writing JSON", detail=f"Serialized {len(rows)} items"))

        with open(target, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)

        return target

    def _json_to_csv(self, source: Path, target: Path, job: ConversionJob, progress_cb, is_cancelled) -> Path:
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            if isinstance(data, dict):
                data = [data]
            else:
                raise ValueError("JSON must contain an array of objects or a single object to convert to CSV.")

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled.")

        fieldnames = []
        has_nested = False
        for item in data:
            if isinstance(item, dict):
                for k, v in item.items():
                    if k not in fieldnames:
                        fieldnames.append(k)
                    if isinstance(v, (dict, list)):
                        has_nested = True

        if has_nested:
            job.warnings.append("Nested objects/arrays in JSON were flattened into JSON-encoded strings.")

        with open(target, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for item in data:
                if isinstance(item, dict):
                    flat_row = {
                        k: json.dumps(v) if isinstance(v, (dict, list)) else v
                        for k, v in item.items()
                    }
                    writer.writerow(flat_row)

        return target

    def _json_to_yaml(self, source: Path, target: Path, progress_cb, is_cancelled) -> Path:
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled.")

        with open(target, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

        return target

    def _yaml_to_json(self, source: Path, target: Path, progress_cb, is_cancelled) -> Path:
        with open(source, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled.")

        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return target

    def _xml_to_json(self, source: Path, target: Path, progress_cb, is_cancelled) -> Path:
        # Use defusedxml to guard against XML entity expansion / XXE
        tree = ET.parse(str(source))
        root = tree.getroot()

        def parse_node(node):
            res = {}
            if node.attrib:
                res["@attributes"] = node.attrib
            children = list(node)
            if children:
                for child in children:
                    tag = child.tag
                    child_val = parse_node(child)
                    if tag in res:
                        if isinstance(res[tag], list):
                            res[tag].append(child_val)
                        else:
                            res[tag] = [res[tag], child_val]
                    else:
                        res[tag] = child_val
            else:
                text = (node.text or "").strip()
                if res:
                    if text:
                        res["#text"] = text
                else:
                    return text
            return res

        data = {root.tag: parse_node(root)}

        with open(target, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return target

    def _json_to_xml(self, source: Path, target: Path, progress_cb, is_cancelled) -> Path:
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)

        root = standard_ET.Element("root")

        def build_xml(parent, val):
            if isinstance(val, dict):
                for k, v in val.items():
                    elem = standard_ET.SubElement(parent, str(k).replace(" ", "_"))
                    build_xml(elem, v)
            elif isinstance(val, list):
                for item in val:
                    elem = standard_ET.SubElement(parent, "item")
                    build_xml(elem, item)
            else:
                parent.text = str(val)

        build_xml(root, data)
        tree = standard_ET.ElementTree(root)
        tree.write(str(target), encoding="utf-8", xml_declaration=True)
        return target

    def _convert_line_endings(self, source: Path, target: Path, to_crlf: bool, progress_cb) -> Path:
        with open(source, "rb") as f:
            content = f.read()

        # Normalize to LF then convert to target
        normalized = content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        if to_crlf:
            final_content = normalized.replace(b"\n", b"\r\n")
        else:
            final_content = normalized

        with open(target, "wb") as f:
            f.write(final_content)

        return target

    def _convert_encoding(self, source: Path, target: Path, target_encoding: str, progress_cb) -> Path:
        # Detect source encoding cleanly
        raw = source.read_bytes()
        decoded = None
        for enc in ("utf-8", "utf-16", "cp1252", "latin-1"):
            try:
                decoded = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if decoded is None:
            decoded = raw.decode("utf-8", errors="replace")

        with open(target, "w", encoding=target_encoding, errors="replace") as f:
            f.write(decoded)

        return target
