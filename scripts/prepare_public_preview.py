"""Audit/stage a local synthetic source candidate; never authorize or publish a release."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import sys
import tomllib
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from public_provenance import transform, validate_structured_references
import yaml

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = "docs/release/public-preview-files.json"
FORBIDDEN = {".git", ".venv", ".codex", ".agents", ".aws", "private", "local", "outputs", "subprojects", "__pycache__"}
FORBIDDEN_PREFIXES = ("docs/research/", "docs/history/", "docs/studies/", "templates/study/", "docs/handoffs/")
REQUIRED = {"README.md", "LICENSE", "pyproject.toml", ".python-version", "requirements-validation.lock", "requirements-build.lock", "src/agent_agriculture/cli.py", "scripts/reconcile.py"}
OWNER_GATES = ["final included-content attribution/ownership and component rights review",
               "final artifact/privacy and approved clean source-only Git-history review",
               "GitHub private reporting activation and responsible triage/notifications",
               "reviewed exact tree/version, public commit identity, visibility and explicit publication authority"]


def safe_name(name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Use a portable explicit relative member path")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or str(path) != name or name == "DRAFT-MANIFEST.json":
        raise ValueError("Unsafe/reserved member path: " + name)
    if any(p in FORBIDDEN or p.startswith(".env") or p.endswith((".pem", ".key")) for p in path.parts) or name.startswith(FORBIDDEN_PREFIXES):
        raise ValueError("Private/history/study/generated material excluded: " + name)
    return path


def selected_source(root, name):
    relative = safe_name(name)
    path = root / name
    if not path.is_file() or any((root.joinpath(*relative.parts[:n])).is_symlink() for n in range(1, len(relative.parts) + 1)):
        raise ValueError("Missing or linked selected source: " + name)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Selected source escapes project")
    return path


def inspect(root=ROOT):
    root = Path(root).resolve()
    spec = json.loads((root / INVENTORY).read_text(encoding="utf-8"))
    if spec.get("status") not in {"private_local_draft_only", "local_source_candidate_only"} or not isinstance(spec.get("files"), list):
        raise ValueError("Explicit local source inventory required")
    files, payloads = [], {}
    for entry in spec["files"]:
        name, source = entry["path"], entry.get("source", entry["path"])
        safe_name(name)
        if name in payloads:
            raise ValueError("Duplicate target member: " + name)
        raw = selected_source(root, source).read_bytes()
        source_sha256 = hashlib.sha256(raw).hexdigest()
        transform_id = entry.get("export_transform")
        if transform_id is not None:
            raw = transform(name, raw, transform_id)
        payloads[name] = raw
        files.append({"path": name, "source": source, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                      "source_sha256": source_sha256, "export_transform": transform_id,
                      "category": entry["category"], "rights_review": entry["rights_review"]})
    if not REQUIRED <= set(payloads):
        raise ValueError("Source draft lacks mandatory install/source files")
    if spec.get("project_license_expression") is not None:
        project = tomllib.loads(payloads["pyproject.toml"].decode("utf-8"))["project"]
        if spec["project_license_expression"] != "MIT" or project.get("license") != "MIT":
            raise ValueError("Selected licence declaration and package metadata disagree")
        if not {"LICENSE", "THIRD_PARTY_NOTICES.md"} <= set(project.get("license-files", [])) or "THIRD_PARTY_NOTICES.md" not in payloads:
            raise ValueError("MIT source candidate must retain its scope and third-party notices")
        if payloads["LICENSE"].splitlines()[:1] != [b"MIT License"] or b"No public redistribution licence is granted" in payloads["LICENSE"]:
            raise ValueError("MIT metadata cannot describe the old private-only licence")
    links = 0
    for name, raw in payloads.items():
        if not name.endswith(".md"):
            continue
        text = raw.decode("utf-8")
        if "\ufffd" in text:
            raise ValueError("Replacement character in selected document")
        for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            target = target.split("#", 1)[0]
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target)).rstrip("/")
            if resolved.startswith("../") or not (resolved in payloads or any(p.startswith(resolved + "/") for p in payloads)):
                raise ValueError("Selected document link is outside draft: " + name + " -> " + target)
            links += 1
    structured = validate_structured_references(payloads)
    tree = [{"path": item["path"], "sha256": item["sha256"]} for item in sorted(files, key=lambda item: item["path"])]
    tree_sha256 = hashlib.sha256(json.dumps(tree, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    report = {"state": "checked_local_source_candidate", "public_release_ready": False,
              "publication_authorized": False, "technical_inventory_passed": True,
              "runtime_basis": "0.1.0a3 MIT source; a2 behavior, engine version and declared export schema differ",
              "files": sorted(files, key=lambda item: item["path"]), "file_count": len(files),
              "selected_bytes": sum(len(v) for v in payloads.values()), "local_document_links": links,
              "structured_evidence_references": structured, "exported_content_tree_sha256": tree_sha256,
              "project_license_private_only": b"No public redistribution licence is granted" in payloads["LICENSE"],
              "project_license_expression": spec.get("project_license_expression"),
              "reporting_route_selected": spec.get("reporting_route_selected"),
              "reporting_activation_verified": False,
              "open_owner_gates": OWNER_GATES,
              "limits": "Explicit file selection and hashes are not a legal clearance, secret-free guarantee, field study, security audit or publication permission."}
    return report, payloads


def stage_draft(output, root=ROOT):
    root = Path(root).resolve()
    report, payloads = inspect(root)
    base = root / "outputs"
    if base.is_symlink() or not base.resolve().is_relative_to(root):
        raise ValueError("Use the project's real local outputs directory")
    output = Path(output).resolve()
    if not output.is_relative_to(base.resolve()) or output == base.resolve() or output.exists():
        raise ValueError("Choose a fresh directory inside project outputs")
    output.parent.mkdir(parents=True, exist_ok=True)
    pending = output.parent / (".public-draft-" + uuid.uuid4().hex)
    pending.mkdir()
    for name, raw in payloads.items():
        path = pending / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    with (pending / "DRAFT-MANIFEST.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")
    # Both absolute targets were checked under project outputs before this rename.
    pending.rename(output)
    verify_draft(output)
    return dict(report, draft_path=str(output))


def verify_draft(folder):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / "DRAFT-MANIFEST.json").read_text(encoding="utf-8"))
    if manifest.get("public_release_ready") is not False or manifest.get("publication_authorized") is not False:
        raise ValueError("This verifier accepts unpublished local draft manifests only")
    if manifest.get("reporting_activation_verified", False) is not False:
        raise ValueError("Local draft verification cannot attest remote reporting activation")
    seen, payloads = set(), {}
    for entry in manifest["files"]:
        name = entry["path"]
        if name in seen:
            raise ValueError("Duplicate declared draft member")
        seen.add(name)
        raw = selected_source(folder, name).read_bytes()
        if len(raw) != entry["bytes"] or hashlib.sha256(raw).hexdigest() != entry["sha256"]:
            raise ValueError("Changed draft member: " + name)
        payloads[name] = raw
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()}
    if actual != seen | {"DRAFT-MANIFEST.json"}:
        raise ValueError("Unexpected or missing draft file")
    structured = validate_structured_references(payloads)
    return {"state": "verified_local_source_candidate", "files": len(seen), "public_release_ready": False,
            "structured_evidence_references": structured}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--stage-draft", type=Path)
    group.add_argument("--verify-draft", type=Path)
    args = parser.parse_args()
    try:
        report = verify_draft(args.verify_draft) if args.verify_draft else (stage_draft(args.stage_draft) if args.stage_draft else inspect()[0])
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        parser.exit(2, "Source draft refused: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
