"""Universal adapter for plant shift-report tabular text.

This adapter consumes externally supplied report text such as a tab-separated
hourly shift report. It performs deterministic tabular normalization only:
date + hourly period -> timestamp, column name -> tag, numeric cell -> value.

It does not infer units, quality, limits, alarms, trends, predictions, or
control actions. Tenant identity is supplied by the caller and is preserved.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from typing import Iterable, Iterator

from .contracts import IndustrialPoint
from .source_adapters import ReadOnlySourceAdapter

_DATE_RE = re.compile(r"^\s*DATE\s*$", re.IGNORECASE)
_PERIOD_RE = re.compile(
    r"^\s*(\d{1,2}):00\s*Hrs\s*-\s*(\d{1,2}):00\s*Hrs\s*$",
    re.IGNORECASE,
)


def _parse_report_date(text: str) -> datetime:
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text.strip(), fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError("shift report DATE must be MM/DD/YYYY, DD/MM/YYYY, or YYYY-MM-DD")


def _first_nonempty(row: list[str]) -> str:
    for cell in row:
        if str(cell).strip():
            return str(cell).strip()
    return ""


def _find_date(rows: list[list[str]]) -> datetime:
    for index, row in enumerate(rows):
        if row and _DATE_RE.match(str(row[0] or "")):
            value = _first_nonempty(row[1:])
            if value:
                return _parse_report_date(value)
            if index + 1 < len(rows):
                value = _first_nonempty(rows[index + 1])
                if value:
                    return _parse_report_date(value)
    raise ValueError("shift report DATE row is required")


def _find_header(rows: list[list[str]]) -> tuple[int, list[str]]:
    for index, row in enumerate(rows):
        if not row:
            continue
        first = str(row[0] or "").strip().lower()
        if "1 hr." in first and "avg" in first:
            return index, [str(cell or "").strip() for cell in row]
    raise ValueError("shift report hourly header is required")


def parse_shift_report_text(
    text: str,
    *,
    plant_id: str,
    source: str = "TATA METALIKS SHIFT MATERIAL REPORT",
) -> Iterator[IndustrialPoint]:
    """Yield one IndustrialPoint for every numeric report cell.

    The input is expected to be tab-separated text copied/exported from a
    spreadsheet. Blank/non-numeric cells are ignored rather than repaired.
    The hourly period is mapped to its start time. No units or quality values
    are invented.
    """
    plant_id = str(plant_id or "").strip()
    source = str(source or "").strip()
    if not plant_id:
        raise ValueError("plant_id is required")
    if not source:
        raise ValueError("source is required")
    if not str(text or "").strip():
        raise ValueError("shift report text is required")

    rows = list(csv.reader(io.StringIO(str(text)), delimiter="\t"))
    report_date = _find_date(rows)
    header_index, headers = _find_header(rows)

    if len(headers) < 2:
        raise ValueError("shift report must contain at least one tag column")

    for row in rows[header_index + 1 :]:
        if not row:
            continue
        match = _PERIOD_RE.match(str(row[0] or "").strip())
        if not match:
            continue
        hour = int(match.group(1))
        if hour > 23:
            raise ValueError(f"invalid hourly period: {row[0]}")
        timestamp = report_date.replace(
            hour=hour, minute=0, second=0, microsecond=0
        ).isoformat()

        for index, raw_value in enumerate(row[1:], start=1):
            if index >= len(headers):
                break
            tag = headers[index].strip()
            value_text = str(raw_value or "").strip()
            if not tag or not value_text:
                continue
            try:
                value = float(value_text)
            except ValueError:
                continue
            yield IndustrialPoint(
                plant_id=plant_id,
                tag=tag,
                timestamp=timestamp,
                value=value,
                source=source,
                mode="HISTORICAL",
                quality="UNKNOWN",
                state="UNKNOWN",
            )


class ShiftReportSourceAdapter(ReadOnlySourceAdapter):
    """Read-only adapter for an externally supplied shift-report export."""

    mode = "HISTORICAL"

    def __init__(
        self,
        report_text: str,
        *,
        name: str = "SHIFT REPORT",
    ) -> None:
        self.name = str(name or "SHIFT REPORT").strip()
        self._report_text = str(report_text or "")

    def read(self, plant_id: str) -> Iterable[IndustrialPoint]:
        plant_id = str(plant_id or "").strip()
        if not plant_id:
            raise ValueError("plant_id is required")
        yield from parse_shift_report_text(
            self._report_text,
            plant_id=plant_id,
            source=self.name,
        )


__all__ = ["parse_shift_report_text", "ShiftReportSourceAdapter"]
