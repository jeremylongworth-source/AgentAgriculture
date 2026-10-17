"""Inventory retained wheel licence evidence in a pinned local preview; no clearance."""

import argparse
from email.parser import BytesParser
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import sys
import zipfile


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(path, expected_sha256):
    if not re.fullmatch(r"[a-fA-F0-9]{64}", expected_sha256):
        raise ValueError("Explicit pinned archive SHA-256 required")
    raw = Path(path).read_bytes()
    if sha256(raw) != expected_sha256.lower():
        raise ValueError("Archive differs from selected qualification evidence")
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        names = bundle.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archive members")
        manifest = json.loads(bundle.read("bundle-manifest.json"))
        declared = {}
        for item in manifest["files"]:
            name = item["path"]
            if name in declared or sha256(bundle.read(name)) != item["sha256"] or len(bundle.read(name)) != item["bytes"]:
                raise ValueError("Manifest member differs")
            declared[name] = item
        if set(names) != set(declared) | {"bundle-manifest.json"}:
            raise ValueError("Archive membership differs")
        root_license = bundle.read("LICENSE")
        components = []
        for name in sorted(names):
            if not name.endswith(".whl"):
                continue
            wheel_raw = bundle.read(name)
            with zipfile.ZipFile(io.BytesIO(wheel_raw)) as wheel:
                wheel_names = wheel.namelist()
                if len(wheel_names) != len(set(wheel_names)):
                    raise ValueError("Duplicate wheel members")
                metadata_names = [n for n in wheel_names if n.endswith(".dist-info/METADATA")]
                if len(metadata_names) != 1:
                    raise ValueError("One metadata record required per wheel")
                metadata_path = metadata_names[0]
                metadata = BytesParser().parsebytes(wheel.read(metadata_path))
                if not metadata["Name"] or not metadata["Version"]:
                    raise ValueError("Component identity missing")
                dist_info = PurePosixPath(metadata_path).parent
                evidence = []
                for declared_file in metadata.get_all("License-File", []):
                    relative = PurePosixPath(declared_file)
                    if relative.is_absolute() or ".." in relative.parts or "\\" in declared_file:
                        raise ValueError("Unsupported declared licence path")
                    candidates = [str(dist_info / "licenses" / relative), str(dist_info / relative)]
                    matches = [candidate for candidate in candidates if candidate in wheel_names]
                    if len(matches) != 1:
                        raise ValueError("Declared licence missing or ambiguous")
                    body = wheel.read(matches[0])
                    if not body.strip():
                        raise ValueError("Empty declared licence")
                    evidence.append({"declared": declared_file, "path": matches[0], "sha256": sha256(body), "bytes": len(body)})
                retained = []
                for member in wheel_names:
                    if any(token in PurePosixPath(member).name.lower() for token in ("license", "copying", "notice")):
                        body = wheel.read(member)
                        retained.append({"path": member, "sha256": sha256(body), "bytes": len(body)})
                if not evidence and not retained:
                    raise ValueError("No retained licence/notice evidence")
                project = metadata["Name"].lower().replace("_", "-") == "agent-agriculture"
                if project and not any(item["sha256"] == sha256(root_license) for item in retained):
                    raise ValueError("Project licence differs between root and wheel")
                components.append({"name": metadata["Name"], "version": metadata["Version"],
                    "wheel_path": name, "wheel_sha256": sha256(wheel_raw), "project_component": project,
                    "license_expression": metadata["License-Expression"], "legacy_license_field": metadata["License"],
                    "license_classifiers": [value for value in metadata.get_all("Classifier", []) if value.startswith("License ::")],
                    "declared_license_evidence": evidence, "retained_notice_files": retained,
                    "redistribution_approved": False})
        if sum(item["project_component"] for item in components) != 1:
            raise ValueError("Exactly one project component required")
    return {"report_version": "1.0.0", "archive_sha256": sha256(raw), "archive_members": len(names),
            "manifest_verified": True, "root_license_sha256": sha256(root_license), "components": components,
            "component_count": len(components), "distribution_clearance": "not_assessed",
            "transitive_binary_component_audit": "not_performed",
            "limits": "Metadata and retained notices are evidence for owner review, not a legal determination or release authority."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        print(json.dumps(inventory(args.archive, args.expected_sha256), ensure_ascii=False, sort_keys=True, indent=2))
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile):
        print(json.dumps({"error": "rights_inventory.invalid", "message": "Archive, manifest, metadata or retained notices differ; no inventory confirmed."}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
