"""Storage helpers for bronze layer persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable


def save_records(source: str, records: Iterable[Dict], project_root: Path | None = None) -> Path:
    base = project_root or Path(__file__).resolve().parents[2]
    now = datetime.utcnow()
    partition = now.strftime("%Y-%m-%d")
    output_dir = base / "data_lake" / "bronze" / source / f"ingestion_date={partition}"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{source}_{now.strftime('%H%M%S')}.jsonl"
    with output_file.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return output_file
