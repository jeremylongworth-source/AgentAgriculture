"""Immutable local snapshots with an OS lock and an atomic current selector."""

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from .contracts import load_document
from .errors import PipelineError


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _write_file(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _replace_selector(root, value):
    temporary = root / (".current-" + uuid.uuid4().hex + ".tmp")
    _write_file(temporary, json_bytes(value))
    os.replace(temporary, root / "current.json")


def write_new_directory(output, payloads, exists_code):
    """Prepare a new local directory; never replace an existing destination."""
    output = Path(output).resolve()
    if output.exists():
        raise PipelineError(exists_code, "Choose a new local output directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.parent / (".preparing-" + uuid.uuid4().hex)
    stage.mkdir()
    for relative, raw in payloads.items():
        _write_file(stage / relative, raw)
    stage.rename(output)
    return output


@contextmanager
def _writer_lock(root):
    root.mkdir(parents=True, exist_ok=True)
    with (root / ".writer-lock").open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell():
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        acquired = False
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            raise PipelineError("output.busy", "Another writer holds the local output lock; retry after it finishes.") from None
        try:
            yield
        finally:
            if acquired:
                stream.seek(0)
                if os.name == "nt":
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def verify_snapshot(folder: Path):
    folder = folder.resolve()
    if not re.fullmatch(r"run-[a-f0-9]{64}", folder.name) or folder.is_symlink():
        raise PipelineError("output.incomplete", "Select a committed run directory; pending directories are not complete.")
    try:
        marker = load_document(folder / "COMPLETED.json")
        raw_manifest = (folder / "package-manifest.json").read_bytes()
        if marker["run_id"] != folder.name or marker["state"] != "complete" or digest(raw_manifest) != marker["package_manifest_sha256"]:
            raise ValueError("Completion marker differs")
        manifest = load_document(folder / "package-manifest.json")
        seen = set()
        for item in manifest["files"]:
            relative = item["path"]
            if not isinstance(relative, str) or ":" in relative or "\\" in relative or relative.startswith("/") or ".." in relative.split("/") or relative in seen:
                raise ValueError("Unsafe or duplicate package path")
            seen.add(relative)
            path = folder / relative
            if not path.resolve().is_relative_to(folder) or path.is_symlink() or digest(path.read_bytes()) != item["sha256"]:
                raise ValueError("Package content differs")
        actual = {path.relative_to(folder).as_posix() for path in folder.rglob("*") if path.is_file()}
        if actual != seen | {"package-manifest.json", "COMPLETED.json"}:
            raise ValueError("Package membership differs")
        identity = {"task": load_document(folder / "task.json"), "manifest": load_document(folder / "input-manifest.json"),
                    "corrections": load_document(folder / "corrections.json"), "engine": marker["engine"]}
        if "run-" + digest(json_bytes(identity)) != folder.name:
            raise ValueError("Input/engine fingerprint differs")
    except (OSError, ValueError, KeyError, TypeError):
        raise PipelineError("output.integrity", "Snapshot is missing, incomplete or changed; originals and older outputs were not overwritten.") from None
    return marker


def publish(root: Path, run_id, payloads, media, engine, task_id):
    root = root.resolve()
    final = root / run_id
    with _writer_lock(root):
        selector_path = root / "current.json"
        selector = load_document(selector_path) if selector_path.exists() else {"schema_version": "1.0.0", "tasks": {}}
        previous = selector["tasks"].get(task_id)
        old_folder = None
        if previous:
            if not re.fullmatch(r"run-[a-f0-9]{64}", previous["run_id"]):
                raise PipelineError("output.selector", "Current selector contains an invalid run identity.")
            old_folder = root / previous["run_id"]
            verify_snapshot(old_folder)
        reused = final.exists()
        if reused:
            verify_snapshot(final)
        else:
            stage = root / (".pending-" + run_id[4:] + "-" + uuid.uuid4().hex)
            stage.mkdir()
            for relative, raw in sorted(payloads.items()):
                _write_file(stage / relative, raw)
            package_manifest = {"schema_version": "1.0.0", "run_id": run_id,
                                "files": [{"path": path, "media_type": media[path], "sha256": digest(raw)} for path, raw in sorted(payloads.items())]}
            raw_manifest = json_bytes(package_manifest)
            _write_file(stage / "package-manifest.json", raw_manifest)
            _write_file(stage / "COMPLETED.json", json_bytes({"schema_version": "1.0.0", "run_id": run_id, "state": "complete", "engine": engine, "package_manifest_sha256": digest(raw_manifest)}))
            # Pending work is retained on failure. Only this rename publishes it.
            stage.rename(final)
            verify_snapshot(final)
        if not previous or previous["run_id"] != run_id:
            old_calcs = {item["calculation_id"]: item for item in load_document(old_folder / "calculations.json")} if old_folder else {}
            new_calcs = {item["calculation_id"]: item for item in load_document(final / "calculations.json")}
            old_engine = load_document(old_folder / "COMPLETED.json")["engine"] if old_folder else engine
            invalidated = sorted(key for key, value in old_calcs.items() if old_engine != engine or value != new_calcs.get(key))
            selector["tasks"][task_id] = {"run_id": run_id, "revision": previous["revision"] + 1 if previous else 1,
                                          "supersedes": previous["run_id"] if previous else None,
                                          "invalidated_calculation_ids": invalidated}
            _replace_selector(root, selector)
        return {"run_id": run_id, "path": str(final), "reused": reused, "revision": selector["tasks"][task_id]["revision"],
                "package_status": load_document(final / "review-package.json")["status"], "delivery_state": "saved_locally"}
