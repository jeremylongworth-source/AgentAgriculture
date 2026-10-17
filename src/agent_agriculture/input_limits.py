"""Approved selected-CSV envelope; never accept a truncated prefix as evidence."""

from .errors import PipelineError

MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_TASK_BYTES = 32 * 1024 * 1024
MAX_TASK_RECORDS = 10_000
READ_CHUNK_BYTES = 64 * 1024


def policy():
    return {"id": "selected-csv-envelope-v1", "max_bytes_per_source": MAX_SOURCE_BYTES,
            "max_combined_input_bytes": MAX_TASK_BYTES, "max_logical_data_records_per_task": MAX_TASK_RECORDS,
            "header_counts_as_record": False, "on_excess": "refuse_without_truncation"}


class InputBudget:
    """One budget per task, shared by both selected sources and all parsed rows."""

    def __init__(self):
        self.bytes = 0
        self.records = 0

    def read(self, path):
        remaining = MAX_TASK_BYTES - self.bytes
        limit = min(MAX_SOURCE_BYTES, remaining)
        raw = bytearray()
        # Actual reads, not file metadata, determine size. The one excess byte
        # detects an oversized/growing source without reading its remaining tail.
        with path.open("rb") as stream:
            while True:
                chunk = stream.read(min(READ_CHUNK_BYTES, limit + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > MAX_SOURCE_BYTES:
                    raise PipelineError("input.source_bytes", "A selected CSV exceeds 16 MiB; retain the original and select a narrower explicit scope.")
                if len(raw) > remaining:
                    raise PipelineError("input.task_bytes", "Selected CSVs exceed 32 MiB combined; retain originals and select a narrower explicit scope.")
        self.bytes += len(raw)
        return bytes(raw)

    def count_record(self):
        self.records += 1
        if self.records > MAX_TASK_RECORDS:
            raise PipelineError("input.task_records", "Selected CSVs exceed 10000 logical data records combined; no truncated result was saved.")
