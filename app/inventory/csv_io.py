from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Callable, Iterable


@dataclass
class ImportResult:
    imported: int
    errors: list[dict]

    def as_response(self) -> dict:
        return {"imported": self.imported, "errors": self.errors}


def parse_csv(text: str) -> tuple[list[str], list[dict]]:
    buf = io.StringIO(text)
    reader = csv.DictReader(buf)
    rows = list(reader)
    return reader.fieldnames or [], rows


def serialize_csv(fieldnames: list[str], rows: Iterable[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in fieldnames})
    return buf.getvalue()


def import_rows(
    rows: list[dict],
    required: list[str],
    handler: Callable[[dict], None],
) -> ImportResult:
    imported = 0
    errors: list[dict] = []
    for idx, row in enumerate(rows, start=1):
        try:
            missing = [k for k in required if not (row.get(k) or "").strip()]
            if missing:
                raise ValueError(f"missing required fields: {','.join(missing)}")
            handler(row)
            imported += 1
        except Exception as exc:  # noqa: BLE001
            errors.append({"row": idx, "error": str(exc), "data": row})
    return ImportResult(imported=imported, errors=errors)
