"""A local, minimized adviser copy; no transmission or external receipt."""

from datetime import datetime, timezone
from pathlib import Path

from .contracts import load_document
from .language import text
from .presentation import escaped, summary
from .storage import digest, json_bytes, verify_snapshot, write_new_directory


def prepare_handoff(run_path, output):
    run_path = Path(run_path).resolve()
    marker = verify_snapshot(run_path)
    review = load_document(run_path / "review-package.json")
    language = review["language"]
    names = ("summary.md", "record-review.md", "calculations.json", "exceptions.json")
    payloads = {name: (run_path / name).read_bytes() for name in names}
    payloads["summary.md"] = summary(load_document(run_path / "task.json"), load_document(run_path / "totals.json"),
                                     load_document(run_path / "exceptions.json"), load_document(run_path / "input-manifest.json"), minimized=True)
    manifest = {"schema_version": "1.0.0", "state": "prepared_local_handoff", "source_run_id": marker["run_id"],
                "created_at": datetime.now(timezone.utc).isoformat(), "language": language,
                "question": review["question"], "scope": review["scope"], "source_package_status": review["status"],
                "intended_recipient_scope": review["intended_recipient_scope"], "source_refs": review["source_refs"],
                "omissions": review["omissions"] + [text(language, "handoff.omitted")],
                "files": [{"path": name, "sha256": digest(raw)} for name, raw in payloads.items()]}
    lines = ["# " + text(language, "handoff.index"), "", escaped(review["question"]), "",
             text(language, "recipient") + ": " + escaped(review["intended_recipient_scope"]), "",
             text(language, "status") + ": " + text(language, review["status"]), ""]
    lines.extend("- `" + name + "`" for name in names)
    lines.extend(["", text(language, "handoff.omitted"), "", text(language, "limits"), ""])
    payloads["index.md"] = "\n".join(lines).encode("utf-8")
    manifest["files"].append({"path": "index.md", "sha256": digest(payloads["index.md"])})
    payloads["handoff.json"] = json_bytes(manifest)
    destination = write_new_directory(output, payloads, "handoff.exists")
    return {"state": "prepared_local_handoff", "path": str(destination), "source_run_id": marker["run_id"],
            "source_package_status": review["status"], "message": text(language, "handoff.saved")}
