"""Bounded, explicit-path persistence for synthetic evaluation artifacts.

This validates this writer's destinations; it is not an operating-system sandbox.
The runner still owns agent isolation, read permissions and experiment identity.
"""
import argparse
import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

NAMES = ("brief.md", "review.json", "activity.json")
MAX_ENCODED_CHUNK = 4096
MAX_CHUNKS = 128
MAX_ARTIFACT_BYTES = 262144
ASSIGNMENT = "capture-assignment.json"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError("Duplicate JSON key: " + key)
            value[key] = item
        return value

    def invalid(value):
        raise ValueError("Nonfinite JSON value: " + value)

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def reject_link(path):
    if path.is_symlink() or path.is_junction():
        raise ValueError("Linked capture paths are unsupported: " + str(path))


def checked_cell(cell, cell_id):
    cell = Path(cell)
    if not cell.is_absolute():
        raise ValueError("--cell must be an absolute prepared case path")
    reject_link(cell)
    cell = cell.resolve(strict=True)
    assignment_path = cell / ASSIGNMENT
    reject_link(assignment_path)
    assignment = strict_json(assignment_path.read_bytes())
    if (not isinstance(assignment, dict) or assignment.get("cell_id") != cell_id or assignment.get("synthetic_only") is not True
            or assignment.get("cell_root") != str(cell)):
        raise ValueError("Prepared cell assignment does not match")
    inventory_path = cell / "inventory.json"
    reject_link(inventory_path)
    raw = inventory_path.read_bytes()
    if digest(raw) != assignment.get("inventory_sha256"):
        raise ValueError("Prepared source inventory changed")
    inventory = strict_json(raw)
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError("Source inventory must be a nonempty object")
    for name, expected in inventory.items():
        if (not isinstance(name, str) or "\\" in name or ":" in name
                or any(part in ("", ".", "..") for part in name.split("/"))
                or name.split("/")[0] in ("outputs", ASSIGNMENT, "inventory.json")
                or not isinstance(expected, str) or not re.fullmatch("[0-9a-f]{64}", expected)):
            raise ValueError("Invalid source inventory member")
        source = cell
        for part in name.split("/"):
            source = source / part
            reject_link(source)
        if not source.resolve(strict=True).is_relative_to(cell) or digest(source.read_bytes()) != expected:
            raise ValueError("Source changed or escaped prepared cell: " + name)
    outputs = cell / "outputs"
    reject_link(outputs)
    if not outputs.is_dir():
        raise ValueError("Prepared outputs directory is absent")
    return cell, outputs, len(inventory)


def artifact_paths(cell, cell_id, name):
    if name not in NAMES:
        raise ValueError("Unknown artifact name")
    _, outputs, count = checked_cell(cell, cell_id)
    parts = outputs / ".capture-parts" / name
    for path in (outputs / ".capture-parts", parts, outputs / name):
        reject_link(path)
    return outputs / name, parts, count


def exclusive_or_identical(path, raw):
    reject_link(path)
    try:
        with path.open("xb") as stream:
            stream.write(raw)
    except FileExistsError:
        if path.read_bytes() != raw:
            raise ValueError("Existing bytes differ; preserved without overwrite: " + str(path))
        return False
    return True


def put_chunk(cell, cell_id, name, index, total, encoded):
    destination, parts, count = artifact_paths(cell, cell_id, name)
    if (type(index) is not int or type(total) is not int
            or not 1 <= total <= MAX_CHUNKS or not 0 <= index < total
            or len(encoded) > MAX_ENCODED_CHUNK):
        raise ValueError("Invalid chunk index/count/size")
    raw = base64.b64decode(encoded, validate=True)
    if not raw:
        raise ValueError("Empty chunks are unsupported")
    parts.mkdir(parents=True, exist_ok=True)
    manifest = json.dumps({"name": name, "total": total}, sort_keys=True).encode("utf-8")
    exclusive_or_identical(parts / "manifest.json", manifest)
    chunk = parts / ("chunk-%03d.bin" % index)
    size = len(raw)
    for previous in parts.glob("chunk-*.bin"):
        reject_link(previous)
        if previous != chunk:
            size += previous.stat().st_size
    if size > MAX_ARTIFACT_BYTES:
        raise ValueError("Artifact byte limit exceeded")
    created = exclusive_or_identical(chunk, raw)
    return {"state": "chunk_saved" if created else "identical_chunk_retained", "artifact": name,
            "index": index, "total": total, "chunk_bytes": len(raw),
            "absolute_destination": str(destination), "source_files_verified": count}


def validate_artifact(name, raw):
    if not raw or len(raw) > MAX_ARTIFACT_BYTES:
        raise ValueError("Artifact byte limit/empty content")
    text = raw.decode("utf-8")
    if name == "brief.md":
        if not text.strip() or len(text.split()) > 550:
            raise ValueError("Brief must contain 1-550 whitespace words")
    elif not isinstance(strict_json(text), dict):
        raise ValueError("Review/activity must be strict JSON objects")


def commit(cell, cell_id, name, expected_sha256):
    destination, parts, count = artifact_paths(cell, cell_id, name)
    if not re.fullmatch("[0-9a-f]{64}", expected_sha256):
        raise ValueError("Expected SHA-256 must be 64 lowercase hex digits")
    manifest_path = parts / "manifest.json"
    reject_link(manifest_path)
    manifest = strict_json(manifest_path.read_bytes())
    if not isinstance(manifest, dict) or manifest.get("name") != name or type(manifest.get("total")) is not int or not 1 <= manifest["total"] <= MAX_CHUNKS:
        raise ValueError("Invalid chunk manifest")
    expected_names = {"manifest.json"} | {"chunk-%03d.bin" % i for i in range(manifest["total"])}
    if {p.name for p in parts.iterdir()} != expected_names:
        raise ValueError("Missing or unexpected chunk members")
    chunks = []
    for index in range(manifest["total"]):
        path = parts / ("chunk-%03d.bin" % index)
        reject_link(path)
        if path.stat().st_size > MAX_ENCODED_CHUNK // 4 * 3:
            raise ValueError("Stored chunk exceeds limit")
        chunks.append(path.read_bytes())
    raw = b"".join(chunks)
    if digest(raw) != expected_sha256:
        raise ValueError("Assembled artifact checksum mismatch")
    validate_artifact(name, raw)
    created = exclusive_or_identical(destination, raw)
    return {"state": "artifact_saved" if created else "identical_artifact_retained", "artifact": name,
            "bytes": len(raw), "sha256": digest(raw), "absolute_destination": str(destination),
            "source_files_verified": count, "utc": datetime.now(timezone.utc).isoformat()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("put", "commit"))
    parser.add_argument("--cell", required=True)
    parser.add_argument("--cell-id", required=True)
    parser.add_argument("--name", required=True, choices=NAMES)
    parser.add_argument("--index", type=int)
    parser.add_argument("--total", type=int)
    parser.add_argument("--base64")
    parser.add_argument("--sha256")
    args = parser.parse_args(argv)
    try:
        if args.operation == "put":
            if args.index is None or args.total is None or args.base64 is None or args.sha256 is not None:
                raise ValueError("put needs --index/--total/--base64 only")
            result = put_chunk(args.cell, args.cell_id, args.name, args.index, args.total, args.base64)
        else:
            if args.sha256 is None or any(v is not None for v in (args.index, args.total, args.base64)):
                raise ValueError("commit needs --sha256 only")
            result = commit(args.cell, args.cell_id, args.name, args.sha256)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"state": "refused", "error": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0
